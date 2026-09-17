import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Cpu, Server } from "lucide-react";
import { api } from "../lib/api";
import { useSentinel } from "../store";
import type { AppConfig } from "../lib/types";

export default function Settings() {
  const ensureSession = useSentinel((s) => s.ensureSession);
  const sessionId = useSentinel((s) => s.sessionId);
  const disposeSession = useSentinel((s) => s.disposeSession);
  const actionsBusy = useSentinel((s) => s.actionsBusy);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    void ensureSession();
    api.config()
      .then(setConfig)
      .catch(() => setConfig(null));
    api.health()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, [ensureSession]);

  return (
    <div className="mx-auto max-w-[1200px] px-4 py-4">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
        <div className="mb-3">
          <h1 className="text-[19px] font-bold tracking-[0.08em] text-text">SETTINGS</h1>
          <p className="mono text-[10.5px] tracking-[0.2em] uppercase text-text-faint">runtime configuration · environment</p>
        </div>

        <div className="grid grid-cols-12 gap-3">
          <div className="col-span-12 lg:col-span-6 panel p-4">
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-amber-bright" />
              <span className="label">PLANNER & BROWSER</span>
            </div>
            <dl className="mt-4 space-y-2.5">
              <Row k="PLANNER" v={config?.planner ?? "…"} />
              <Row k="PROVIDER" v={config?.planner_provider ?? "…"} />
              <Row k="BROWSER MODE" v={config?.headless ? "headless" : "headed"} />
              <Row k="VIEWPORT" v={config ? `${config.viewport[0]} × ${config.viewport[1]}` : "…"} />
              <Row k="APPROVAL TTL" v={config ? `${config.approval_ttl}s` : "…"} />
              <Row k="DEMO HOME" v={config?.home_url ?? "…"} />
              <Row k="CANARY" v={config?.canary_registered ? "SEEDED" : "not seeded"} />
            </dl>
            <p className="mt-4 mono text-[10px] leading-relaxed text-text-faint">
              FULL CONTROL SURFACE LIVES IN THE BACKEND ENV: SENTINEL_OPENAI_API_KEY / SENTINEL_APPROVAL_TTL_SECONDS / SENTINEL_DATA_DIR / SENTINEL_BROWSER_HEADLESS — SEE server/.env.example
            </p>
          </div>

          <div className="col-span-12 lg:col-span-6 space-y-3">
            <div className="panel p-4">
              <div className="flex items-center gap-2">
                <Server className="h-4 w-4 text-cyan" />
                <span className="label">SERVICE HEALTH</span>
              </div>
              {health ? (
                <div className="mt-3 grid grid-cols-2 gap-2">
                  {Object.entries(health).map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between rounded-md bg-black/30 px-3 py-2">
                      <span className="mono text-[10px] uppercase tracking-wide text-text-faint">{k}</span>
                      <span className={`mono text-[11px] ${k === "browser" && String(v).toLowerCase().includes("disconnect") ? "text-coral" : "text-mint"}`}>
                        {String(v)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-3 mono text-[11px] text-text-faint">querying…</div>
              )}
            </div>

            <div className="panel p-4" style={{ borderColor: "rgba(255,107,87,0.3)" }}>
              <span className="label !text-coral">DANGER ZONE</span>
              <p className="mt-2 text-[12.5px] text-text-dim">
                Drop the client session state. The server session stays alive per its own lifecycle; the UI will reconnect on next action.
              </p>
              <button className="btn danger mt-3" onClick={() => disposeSession()} disabled={actionsBusy || !sessionId}>
                DISPOSE CLIENT SESSION
              </button>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-baseline justify-between border-b border-[rgba(35,42,53,0.4)] pb-1.5">
      <span className="mono text-[10px] uppercase tracking-[0.12em] text-text-faint">{k}</span>
      <span className="mono text-[11.5px] text-text">{v}</span>
    </div>
  );
}