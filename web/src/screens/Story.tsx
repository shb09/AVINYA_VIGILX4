import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Film, RotateCcw } from "lucide-react";
import { useSentinel } from "../store";
import { AGENT_ACTIVE } from "../store";
import { ThreatIcon } from "../components/ThreatList";

export default function Story() {
  const snap = useSentinel((s) => s.snap);
  const events = useSentinel((s) => s.events);
  const run = useSentinel((s) => s.run);
  const reset = useSentinel((s) => s.reset);
  const ensureSession = useSentinel((s) => s.ensureSession);
  const [rep, setRep] = useState(0);

  useEffect(() => {
    void ensureSession();
  }, [ensureSession]);

  useEffect(() => {
    setRep((r) => r + 1);
  }, [events.length, snap?.agent.status, snap?.security?.evaluated_at]);

  const active = snap ? AGENT_ACTIVE[snap.agent.status] : false;
  const running = !!(snap && active);

  return (
    <div className="mx-auto max-w-[1500px] px-4 py-4">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
        <div className="mb-3 flex items-center gap-3">
          <div>
            <h1 className="text-[19px] font-bold tracking-[0.08em] text-text">STORY MODE</h1>
            <p className="mono text-[10.5px] tracking-[0.2em] uppercase text-text-faint">one decision, told as a narrative</p>
          </div>
          <div className="ml-auto flex gap-2">
            <button className="btn" onClick={() => void reset()} disabled={running}>
              <RotateCcw className="h-3.5 w-3.5" /> RESET
            </button>
            {!running && !snap?.threats?.length && snap?.agent.status !== "COMPLETED" && (
              <button className="btn primary" onClick={() => void run({ scenario: "attack" })}>
                <Film className="h-3.5 w-3.5" /> RUN ATTACK SCENE
              </button>
            )}
          </div>
        </div>

        <AnimatePresence mode="wait">
          {(!snap || events.length === 0) && (
            <motion.div key="empty" exit={{ opacity: 0 }} className="panel flex aspect-video max-h-[420px] items-center justify-center text-text-faint">
              <span className="mono text-[11px] tracking-[0.2em] uppercase">run a scenario to build a story</span>
            </motion.div>
          )}

          {(snap && events.length > 0) && (
            <motion.div key={rep} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
              {snap.agent.task && (
                <div className="panel p-4">
                  <span className="chip warn mono">THE JOB</span>
                  <p className="mt-2 text-[15px] leading-relaxed text-text">{snap.agent.task}</p>
                </div>
              )}

              {snap.narrative && (
                <div className="panel p-4">
                  <span className="label">AGENT NARRATIVE</span>
                  <p className="mt-2 text-[14px] leading-relaxed text-text-dim font-light">{snap.narrative}</p>
                </div>
              )}

              {snap.threats && snap.threats.length > 0 && (
                <div className="panel p-4" style={{ borderColor: "rgba(255,107,87,0.35)" }}>
                  <span className="chip block mono">THE INJECTED THREAT</span>
                  <div className="mt-3 space-y-3">
                    {snap.threats.map((t, i) => (
                      <StoryThreat key={t.type + i} t={t} i={i} />
                    ))}
                  </div>
                </div>
              )}

              {snap.security && (
                <div className="panel p-4" style={{ borderColor: "rgba(242,184,75,0.4)" }}>
                  <span className="chip warn mono">THE DECISION</span>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span className={`chip ${snap.security.verdict === "ALLOW" ? "allow" : snap.security.verdict === "APPROVAL" ? "approval" : "block"}`}>
                      VERDICT {snap.security.verdict}
                    </span>
                    <span className="chip mono">RISK {snap.security.risk}</span>
                    {snap.security.fail_closed && <span className="chip block mono">FAIL CLOSED</span>}
                  </div>
                  <ul className="mt-3 space-y-1.5">
                    {snap.security.policy_ids.map((p) => (
                      <li key={p} className="mono text-[11.5px] text-amber-bright">▸ {p}</li>
                    ))}
                  </ul>
                  <ul className="mt-2 space-y-1">
                    {snap.security.reasons.map((r, i) => (
                      <li key={i} className="text-[12.5px] text-text-dim">— {r}</li>
                    ))}
                  </ul>
                </div>
              )}

              {!snap.threats?.length && snap.agent.status === "COMPLETED" && (
                <div className="panel p-4" style={{ borderColor: "rgba(123,224,163,0.4)" }}>
                  <span className="chip ok mono">RESOLUTION</span>
                  <p className="mt-2 text-[14px] text-text-dim">
                    The agent finished its job. Every proposed action was evaluated by Sentinel before the browser was allowed to execute it. No instruction left the guardrail.
                  </p>
                </div>
              )}

              {snap.threats && snap.threats.length > 0 && (
                <div className="panel p-4" style={{ borderColor: "rgba(123,224,163,0.3)" }}>
                  <span className="chip ok mono">RESOLUTION</span>
                  <p className="mt-2 text-[14px] text-text-dim">
                    The strategy was contained. The browser performed <b className="text-text">{snap.executed_count}</b> sanctioned action
                    {snap.executed_count === 1 ? "" : "s"}; the injected task never reached the browser.
                  </p>
                </div>
              )}

              {running && (
                <div className="panel flex items-center gap-3 p-3">
                  <span className="h-2 w-2 rounded-full bg-amber-bright pulse-drop" />
                  <span className="mono text-[11px] tracking-[0.14em] uppercase text-text-dim">{snap.agent.status}…</span>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}

function StoryThreat({ t, i }: { t: Parameters<typeof ThreatIcon>[0]["t"]; i: number }) {
  const steps = [
    t.story.what_page_tried,
    t.story.what_agent_proposed,
    t.story.where_going,
    t.story.policy_stopped?.join(", "),
    "Sentinel refused the action. The browser never executed it.",
  ].filter(Boolean);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: i * 0.12 }}
      className="rounded-lg border border-[rgba(255,107,87,0.22)] bg-[rgba(255,107,87,0.05)] p-3"
    >
      <div className="flex items-center gap-2">
        <ThreatIcon t={t} />
        <span className="mono text-[12px] uppercase tracking-wide text-text">{t.title}</span>
        <span className="mono ml-auto text-[10px] uppercase text-coral">{t.severity}</span>
      </div>
      <ol className="mt-3 space-y-2">
        {steps.map((s, idx) => (
          <li key={idx} className="flex gap-2.5 text-[12.5px] leading-relaxed text-text-dim">
            <span className="mono mt-0.5 shrink-0 text-[10px] text-amber-bright">SCENE {idx + 1}</span>
            <span>{s}</span>
          </li>
        ))}
      </ol>
      <div className="mt-2 pl-[68px] mono text-[10px] text-text-faint">THREAT {t.type}</div>
    </motion.div>
  );
}