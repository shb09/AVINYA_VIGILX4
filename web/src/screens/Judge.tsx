import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Brain, Gavel, Radio, RotateCcw } from "lucide-react";
import { useSentinel } from "../store";
import { AGENT_ACTIVE } from "../store";
import ProvenanceView from "../components/ProvenanceView";
import ThreatList from "../components/ThreatList";

const SCENARIOS = [
  { key: "safe", label: "SAFE", blurb: "is a calm browsing session allowed through cleanly?" },
  { key: "attack", label: "ATTACK", blurb: "the page forges instructions to steal a token — does it get through?" },
  { key: "sensitive", label: "SENSITIVE", blurb: "authorization fields — does the agent have to justify itself to you?" },
] as const;

export default function Judge() {
  const ensureSession = useSentinel((s) => s.ensureSession);
  const sessionId = useSentinel((s) => s.sessionId);
  const snap = useSentinel((s) => s.snap);
  const run = useSentinel((s) => s.run);
  const reset = useSentinel((s) => s.reset);
  const approve = useSentinel((s) => s.approve);
  const busy = useSentinel((s) => s.actionsBusy);

  useEffect(() => {
    void ensureSession();
  }, [ensureSession]);

  const running = snap ? AGENT_ACTIVE[snap.agent.status] : false;
  const sec = snap?.security;

  return (
    <div className="mx-auto max-w-[1500px] px-4 py-4">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
        <div className="mb-3 flex items-center gap-3">
          <div>
            <h1 className="flex items-center gap-2 text-[19px] font-bold tracking-[0.08em] text-text">
              <Gavel className="h-5 w-5 text-amber-bright" /> JUDGE MODE
            </h1>
            <p className="mono text-[10.5px] tracking-[0.2em] uppercase text-text-faint">
              one tap · the full pipeline · a verdict, on screen
            </p>
          </div>
          <button className="btn ml-auto" onClick={() => void reset()} disabled={running || busy}>
            <RotateCcw className="h-3.5 w-3.5" /> RESET
          </button>
        </div>

        <div className="grid grid-cols-12 gap-3">
          <div className="col-span-12 lg:col-span-8 space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {SCENARIOS.map((s) => (
                <motion.button
                  key={s.key}
                  whileHover={{ y: -2 }}
                  className="panel p-4 text-left hover:!border-amber/50 transition-colors"
                  disabled={running || busy || !sessionId}
                  onClick={() => void run({ scenario: s.key })}
                >
                  <span className="mono text-[12px] font-bold tracking-[0.12em] text-amber-bright">{s.label}</span>
                  <p className="mt-1.5 text-[12px] leading-relaxed text-text-dim">{s.blurb}</p>
                </motion.button>
              ))}
            </div>

            <AnimatePresence mode="wait">
              {!snap && (
                <motion.div key="empty" exit={{ opacity: 0 }} className="panel flex aspect-video max-h-[320px] items-center justify-center text-text-faint">
                  <span className="mono text-[11px] tracking-[0.2em] uppercase flex items-center gap-2">
                    <Radio className="h-4 w-4 pulse-drop" /> pick a scenario to pass judgement
                  </span>
                </motion.div>
              )}

              {snap && (
                <motion.div key={snap.generation} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
                  <div className="panel p-4" style={{ borderColor: "rgba(242,184,75,0.4)" }}>
                    <div className="flex items-center gap-2">
                      <Brain className="h-4 w-4 text-amber-bright" />
                      <span className="label">VERDICT</span>
                      {sec ? (
                        <span className={`chip ml-auto ${sec.verdict === "ALLOW" ? "allow" : sec.verdict === "APPROVAL" ? "approval" : "block"}`}>
                          {sec.verdict}
                        </span>
                      ) : (
                        <span className="chip ml-auto warn mono">{snap.agent.status}</span>
                      )}
                    </div>
                    {snap.agent.task && (
                      <p className="mt-3 text-[14px] text-text">“{snap.agent.task}”</p>
                    )}
                    {sec && (
                      <>
                        <ul className="mt-3 space-y-1.5">
                          {sec.policy_ids.map((p) => (
                            <li key={p} className="mono text-[11px] text-amber-bright">▸ {p}</li>
                          ))}
                        </ul>
                        <ul className="mt-2 space-y-1">
                          {sec.reasons.map((r, i) => (
                            <li key={i} className="text-[12.5px] text-text-dim">— {r}</li>
                          ))}
                        </ul>
                      </>
                    )}
                  </div>

                  {snap.threats && snap.threats.length > 0 && <ThreatList />}

                  {snap.pending_approval && (
                    <div className="panel p-4" style={{ borderColor: "rgba(94,224,214,0.45)" }}>
                      <span className="chip approval mono">APPROVAL REQUIRED · {snap.pending_approval.exchange}</span>
                      <div className="mt-3 flex gap-2">
                        <button className="btn ok flex-1" disabled={busy} onClick={() => void approve(snap.pending_approval!.action_id, true)}>
                          GRANT
                        </button>
                        <button className="btn danger flex-1" disabled={busy} onClick={() => void approve(snap.pending_approval!.action_id, false)}>
                          DENY
                        </button>
                      </div>
                    </div>
                  )}

                  <div className="panel overflow-hidden" style={{ minHeight: 260 }}>
                    <ProvenanceView />
                  </div>

                  <div className="panel flex items-center gap-3 p-3">
                    <span className={`h-2 w-2 rounded-full ${running ? "bg-amber-bright pulse-drop" : snap.agent.status === "COMPLETED" ? "bg-mint" : snap.agent.status === "BLOCKED" ? "bg-coral" : "bg-cyan"}`} />
                    <span className="mono text-[11px] tracking-[0.14em] uppercase text-text-dim">
                      {running ? `DECIDING — ${snap.agent.status.toLowerCase()}…` : `${snap.agent.status} · ${snap.executed_count} executed · ${snap.audit_count} audited`}
                    </span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <div className="col-span-12 lg:col-span-4">
            <div className="panel p-4">
              <span className="label">HOW TO READ THE VERDICT</span>
              <ul className="mt-3 space-y-2 text-[12.5px] text-text-dim">
                <li><span className="chip allow mono mr-1.5">ALLOW</span> the proposal cleared every policy and the browser was told to run it.</li>
                <li><span className="chip approval mono mr-1.5">APPROVAL</span> the proposal touched a protected surface — you, right now, become the gate. Single-use, bound to one action.</li>
                <li><span className="chip block mono mr-1.5">BLOCK</span> a threat was confirmed. Nothing was executed.</li>
              </ul>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}