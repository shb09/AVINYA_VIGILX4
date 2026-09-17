from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..models.events import EventType, ev

router = APIRouter()


@router.websocket("/ws/{session_id}")
async def ws_endpoint(websocket: WebSocket, session_id: str) -> None:
    services = websocket.app.state.services
    session = services.sessions.sessions.get(session_id)
    if session is None:
        await websocket.close(code=4404)
        return

    client_id, queue = await services.hub.subscribe(session_id)
    await websocket.accept()

    tasks: list[asyncio.Task] = []

    async def writer() -> None:
        try:
            for event in session.events:
                await websocket.send_json(event.model_dump(mode="json"))
            await websocket.send_json({"type": "STATE", "session_id": session_id, "message": None, "data": session.snapshot(), "seq": session.next_seq()})
            while True:
                event = await queue.get()
                await websocket.send_json(event.model_dump(mode="json"))
        except Exception:
            pass

    async def reader() -> None:
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                kind = msg.get("kind")
                if kind == "ping":
                    await websocket.send_json({"type": "PONG", "session_id": session_id, "seq": session.next_seq(), "data": {}, "message": None})
                elif kind == "request_state":
                    await websocket.send_json({"type": "STATE", "session_id": session_id, "message": None, "data": session.snapshot(), "seq": session.next_seq()})
                elif kind == "input":
                    if not session.human_control:
                        await websocket.send_json(
                            {"type": "MESSAGE", "session_id": session_id, "message": "Human control is not active.", "data": {}, "seq": session.next_seq()}
                        )
                        continue
                    try:
                        await services.browser.human_input(session_id, msg.get("payload") or {})
                        await services.browser.stream_screenshot(session_id)
                    except Exception as exc:
                        await websocket.send_json(
                            {"type": "BROWSER_ERROR", "session_id": session_id, "message": str(exc)[:160], "data": {}, "seq": session.next_seq()}
                        )
        except Exception:
            pass

    writer_task = asyncio.create_task(writer())
    reader_task = asyncio.create_task(reader())
    tasks.extend([writer_task, reader_task])

    try:
        try:
            await writer_task
        except asyncio.CancelledError:
            pass
        while reader_task and not reader_task.done():
            await asyncio.wait([reader_task], timeout=0.2)
    except WebSocketDisconnect:  # pragma: no cover
        pass
    finally:
        services.hub.unsubscribe(session_id, client_id)
        for task in tasks:
            task.cancel()