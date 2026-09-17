import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import uvicorn

from app.main import app

PORT = 8100
TERMINAL = {"COMPLETED", "BLOCKED", "FAILED", "STOPPED"}


async def wait_server(base, timeout=40):
    deadline = asyncio.get_event_loop().time() + timeout
    async with httpx.AsyncClient(base_url=base) as client:
        while asyncio.get_event_loop().time() < deadline:
            try:
                r = await client.get("/api/health")
                if r.status_code == 200:
                    return r.json()
            except Exception:
                pass
            await asyncio.sleep(0.25)
    raise RuntimeError("server did not come up")


async def wait_terminal(client, sid, timeout=90):
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        state = (await client.get(f"/api/session/{sid}")).json()
        status = state.get("agent", {}).get("status")
        if status in TERMINAL:
            return state
        await asyncio.sleep(0.2)
    return (await client.get(f"/api/session/{sid}")).json()


async def run_scenario(client, base, scenario):
    sid = (await client.post("/api/session")).json()["session_id"]

    approval_task = None

    async def auto_approve():
        while True:
            state = (await client.get(f"/api/session/{sid}")).json()
            pa = state.get("pending_approval")
            if pa:
                await client.post(f"/api/session/{sid}/approval", json={"action_id": pa["action_id"], "decision": True})
            await asyncio.sleep(0.15)

    if scenario == "sensitive":
        approval_task = asyncio.create_task(auto_approve())

    await client.post(f"/api/session/{sid}/agent/run", json={"scenario": scenario})
    state = await wait_terminal(client, sid)
    if approval_task:
        approval_task.cancel()

    events = (await client.get(f"/api/session/{sid}/events")).json()["events"]
    kinds = [e["type"] for e in events]
    print(f"\n[{scenario.upper()}] status={state['agent']['status']} verdict={state.get('security', {}).get('verdict') if state.get('security') else None}")
    print("  policies:", (state.get("security") or {}).get("policy_ids"))
    print("  error:", state.get("agent", {}).get("error"))
    print("  threats:", [(t["type"], t["title"]) for t in state.get("threats", [])])
    print("  executed:", [(e.get("data", {}).get("action_id"), e.get("data", {}).get("action")) for e in events if e["type"] == "ACTION_EXECUTED"])
    print("  prevented:", [e.get("data", {}).get("action_id") for e in events if e["type"] in ("EXECUTION_PREVENTED", "ACTION_BLOCKED")])
    print("  key events:", [k for k in kinds if k in ("ACTION_PROPOSED", "POLICY_EVALUATED", "APPROVAL_REQUIRED", "APPROVAL_GRANTED", "EXECUTION_PREVENTED", "THREAT_DETECTED")])
    await client.delete(f"/api/session/{sid}")
    return state


async def main():
    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())

    base = f"http://127.0.0.1:{PORT}"
    health = await wait_server(base)
    print("health:", health)

    async with httpx.AsyncClient(base_url=base, timeout=120) as client:
        for scenario in ("safe", "attack", "sensitive"):
            await run_scenario(client, base, scenario)

        # canary containment
        audit = (await client.get("/api/audit")).json()
        canary = app.state.services.settings.canary_seed
        blob = str(audit)
        print("\ncanary in audit API:", canary in blob)

    server.should_exit = True
    await task
    print("\nE2E SMOKE OK")


asyncio.run(main())