import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Brain, Gavel, Radio, RotateCcw, Check, X, AlertCircle } from "lucide-react";
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
  const hasPendingApproval = snap?.pending_approval != null;

  const getVerdictChip = (verdict: string | undefined) => {
    if (!verdict) return null;
    const config = {
      ALLOW: { icon: Check, cls: "chip allow", text: "VERDICT ALLOW", color: "text-mint" },
      APPROVAL: { icon: AlertCircle, cls: "chip approval", text: "VERDICT APPROVAL", color: "text-cyan" },
      BLOCK: { icon: X, cls: "chip block", text: "VERDICT BLOCK", color: "text-coral" },
    };
    const c = config[verdict as keyof typeof config];
    if (!c) return null;

    return (
      <span className={`chip ${c.cls} flex items-center gap-2`}>
        <c.icon className="h-4 w-4" />
        {c.text}
      </span>
    );
  };

  const formatStatusText = (status: string) => {
    switch (status) {
      case "IDLE": return "Agent is idle and ready.";
      case "OBSERVING": return "Agent is scanning the current page...";
      case "PLANNING": return "Agent is planning the next actions...";
      case "PROPOSING": return "Agent has proposed an action for Sentinel...";
      case "WAITING_FOR_AUTHORIZATION": return "Sentinel is evaluating the action...";
      case "WAITING_FOR_APPROVAL": return "Sentinel requires human approval for this action...";
      case "EXECUTING": return "Agent is executing the sanctioned action...";
      case "COMPLETED": return "Agent has completed the task successfully.";
      case "BLOCKED": return "Sentinel has blocked the action. No execution.";
      case "FAILED": return "An error occurred during execution.";
      default: return `Agent status: ${status}`;
    }
  };

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
                  <motion.div
                    key="verdict-section"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1, duration: 0.3 }}
                    className="panel p-4" style={{ borderColor: "rgba(242,184,75,0.4)" }}
                  >
                    <div className="flex items-center gap-2">
                      <Brain className="h-4 w-4 text-amber-bright" />
                      <span className="label">VERDICT</span>
                      {getVerdictChip(sec?.verdict)}
                      {sec ? (
                        <span className={`chip ml-auto ${sec.verdict === "ALLOW" ? "allow" : sec.verdict === "APPROVAL" ? "approval" : "block"}`}>
                          {sec.verdict}
                        </span>
                      ) : (
                        <span className="chip ml-auto warn mono">{snap.agent.status}</span>
                      )}
                    </div>

                    {snap.agent.task && (
                      <div className="mt-4 p-3 rounded-lg bg-[rgba(242,184,75,0.06)] border border-[rgba(242,184,75,0.2)]">
                        <div className="mono text-[11px] text-text-faint uppercase tracking-wide">THE JOB</div>
                        <p className="mt-1 text-[14px] text-text">“{snap.agent.task}”</p>
                      </div>
                    )}

                    {sec && (
                      <div className="mt-4 space-y-3">
                        {sec.policy_ids.length > 0 && (
                          <div>
                            <div className="mono text-[11px] text-text-faint uppercase tracking-wide mb-2">POLICIES APPLIED</div>
                            <ul className="space-y-1">
                              {sec.policy_ids.map((p) => (
                                <li key={p} className="mono flex items-start gap-2 text-[11px] text-amber-bright">
                                  <span className="mt-0.5">▸</span>
                                  {p}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {sec.reasons.length > 0 && (
                          <div>
                            <div className="mono text-[11px] text-text-faint uppercase tracking-wide mb-2">REASONS</div>
                            <ul className="space-y-1">
                              {sec.reasons.map((r, i) => (
                                <li key={i} className="text-[12px] leading-relaxed text-text-dim">
                                  <span className="text-coral mr-1">—</span>
                                  {r}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {sec.risk && (
                          <div>
                            <div className="mono text-[11px] text-text-faint uppercase tracking-wide mb-2">RISK ASSESSMENT</div>
                            <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full mono text-[11px] ${sec.risk === "CRITICAL" ? "text-coral border border-[rgba(255,107,87,0.4)] bg-[rgba(255,107,87,0.08)]" : sec.risk === "HIGH" ? "text-amber-bright border border-[rgba(242,184,75,0.4)] bg-[rgba(242,184,75,0.08)]" : sec.risk === "MEDIUM" ? "text-cyan border border-[rgba(94,224,214,0.4)] bg-[rgba(94,224,214,0.08)]" : "text-mint border border-[rgba(123,224,163,0.4)] bg-[rgba(123,224,163,0.08)]"}>
                              RISK: {sec.risk}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </motion.div>

                  {snap.threats && snap.threats.length > 0 && <ThreatList />}

                  {hasPendingApproval && (
                    <motion.div
                      key="approval-section"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.2, duration: 0.3 }}
                      className="panel p-4" style={{ borderColor: "rgba(94,224,214,0.45)" }}
                    >
                      <span className="chip approval mono">APPROVAL REQUIRED · {snap.pending_approval?.exchange}</span>
                      <div className="mt-3 space-y-2">
                        <div className="text-[13px] text-text-dim">
                          <span className="text-text-faint">Action ID:</span> <span className="text-amber-bright">{snap.pending_approval?.action_id}</span>
                        </div>
                        {snap.pending_approval?.proposal && (
                          <div className="text-[13px] text-text-dim">
                            <span className="text-text-faint">Type:</span> <span className="text-cyan">{snap.pending_approval.proposal.action_type}</span>
                          </div>
                        )}
                      </div>
                      <div className="mt-3 flex gap-2">
                        <button className="btn ok flex-1" disabled={busy} onClick={() => void approve(snap.pending_approval!.action_id, true)}>
                          <Check className="h-3.5 w-3.5" /> GRANT
                        </button>
                        <button className="btn danger flex-1" disabled={busy} onClick={() => void approve(snap.pending_approval!.action_id, false)}>
                          <X className="h-3.5 w-3.5" /> DENY
                        </button>
                      </div>
                    </motion.div>
                  )}

                  <motion.div
                    key="provenance-section"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3, duration: 0.3 }}
                    className="panel overflow-hidden" style={{ minHeight: 260 }}
                  >
                    <ProvenanceView />
                  </motion.div>

                  <motion.div
                    key="agent-status-section"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4, duration: 0.3 }}
                    className="panel flex items-center gap-3 p-3"
                  >
                    <span className={`h-2 w-2 rounded-full ${running ? "bg-amber-bright pulse-drop" : snap.agent.status === "COMPLETED" ? "bg-mint" : snap.agent.status === "BLOCKED" ? "bg-coral" : "bg-cyan"}`} />
                    <span className="mono text-[11px] tracking-[0.14em] uppercase text-text-dim">
                      {running ? `DECIDING — ${formatStatusText(snap.agent.status)}…` : `${snap.agent.status} · ${snap.executed_count} executed · ${snap.audit_count} audited`}
                    </span>
                  </motion.div>
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

              <div className="mt-4 p-3 rounded-lg bg-[rgba(94,224,214,0.06)] border border-[rgba(94,224,214,0.2)]">
                <div className="mono text-[11px] text-text-faint uppercase tracking-wide">JUDGE MODE PURPOSE</div>
                <p className="mt-1 text-[12px] text-text-dim leading-relaxed">
                  Watch the real Sentinel pipeline in action. Each scenario demonstrates how the agent proposes, Sentinel decides, and the browser executes (or is blocked) based on real-time policy evaluation.
                </p>
              </div>

              <div className="mt-3 p-3 rounded-lg bg-[rgba(242,184,75,0.06)] border border-[rgba(242,184,75,0.2)]">
                <div className="mono text-[11px] text-text-faint uppercase tracking-wide">SCENARIO OVERVIEW</div>
                <div className="mt-2 space-y-1.5 text-[12px] text-text-dim">
                  <div className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-mint" />
                    <span>SAFE: normal browsing flow, cleanly approved</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-amber-bright" />
                    <span>SENSITIVE: authorization fields trigger approval gate</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-coral" />
                    <span>ATTACK: malicious injection, Sentinel blocks execution</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}