import { motion, AnimatePresence } from "framer-motion";
import { Ban, Hourglass, ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";
import { useSentinel } from "../store";
import { AGENT_ACTIVE } from "../store";
import type { Verdict } from "../lib/types";

const VERDICT_META: Record<Verdict, { label: string; icon: typeof ShieldCheck; cls: string }> = {
  ALLOW: { label: "ALLOW — execute", icon: ShieldCheck, cls: "chip allow" },
  APPROVAL: { label: "APPROVAL — human gate", icon: Hourglass, cls: "chip approval" },
  BLOCK: { label: "BLOCK — refused", icon: Ban, cls: "chip block" },
};

function fmtTime(ts: number | undefined) {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleTimeString(undefined, { hour12: false });
}

export default function DecisionPanel() {
  const snap = useSentinel((s) => s.snap);
  const sec = snap?.security;

  const active = snap ? AGENT_ACTIVE[snap.agent.status] : false;
  const meta = sec ? VERDICT_META[sec.verdict] : null;

  return (
    <div className="panel p-4">
      <div className="flex items-center justify-between">
        <span className="label">SENTINEL · POLICY DECISION</span>
        {sec && <span className="mono text-[10px] text-text-faint">{fmtTime(sec.evaluated_at)}</span>}
      </div>

      <div className="mt-3 min-h-[96px]">
        <AnimatePresence mode="wait">
          {sec && meta ? (
            <motion.div
              key={sec.evaluated_at}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18 }}
            >
              <div className="flex items-center gap-3">
                <span className={`chip ${meta.cls.split(" ")[1]}`}>
                  <meta.icon className="h-3.5 w-3.5" />
                  {meta.label}
                </span>
                <span className="chip mono text-text-faint">RISK {sec.risk}</span>
                {sec.fail_closed && <span className="chip block mono">FAIL CLOSED</span>}
              </div>

              <ul className="mt-3 space-y-1.5">
                {sec.policy_ids.map((p) => (
                  <li key={p} className="mono flex items-start gap-2 text-[11px] text-text-dim">
                    <span className="mt-0.5 text-amber-bright">▸</span>
                    {p}
                  </li>
                ))}
              </ul>

              <ul className="mt-2 space-y-1">
                {sec.reasons.map((r, i) => (
                  <li key={i} className="text-[12px] leading-relaxed text-text">
                    <span className="text-coral mr-1">—</span>
                    {r}
                  </li>
                ))}
              </ul>
            </motion.div>
          ) : (
            <motion.div
              key="idle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col gap-2 text-text-faint"
            >
              <div className="flex items-center gap-2">
                <ShieldQuestion className="h-4 w-4" />
                <span className="text-[13px] text-text-dim">No proposal evaluated yet.</span>
              </div>
              <p className="mono text-[10px] leading-relaxed tracking-[0.06em] uppercase">
                action_proposal → provenance_chain → policy_id → action_id
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="mt-3 flex items-center gap-2 border-t border-[color:var(--border)] pt-3">
        <span className="chip mono text-text-faint">{snap?.proposal_count ?? 0} PROPOSALS</span>
        <span className="chip mono text-text-faint">{snap?.executed_count ?? 0} EXECUTED</span>
        <span className="chip mono text-text-faint">{snap?.audit_count ?? 0} AUDITED</span>
        {active && <ShieldAlert className="ml-auto h-4 w-4 text-amber-bright pulse-drop" />}
      </div>

      {/* Agent status with enhanced visual feedback */}
      <div className="mt-3 flex items-center justify-between">
        <span className="label">AGENT STATE</span>
        <div className="flex items-center gap-2">
          {snap && snap.agent.status !== "IDLE" && snap.agent.status !== "STOPPED" && snap.agent.status !== "COMPLETED" && snap.agent.status !== "BLOCKED" && snap.agent.status !== "FAILED" && snap.agent.status !== "PAUSED" && (
            <span className={`h-2 w-2 rounded-full pulse-drop ${snap.agent.status === "WAITING_FOR_AUTHORIZATION" ? "bg-amber-bright" : snap.agent.status === "WAITING_FOR_APPROVAL" ? "bg-cyan" : snap.agent.status === "EXECUTING" ? "bg-mint" : snap.agent.status === "PLANNING" ? "bg-amber-bright" : snap.agent.status === "OBSERVING" ? "bg-cyan" : snap.agent.status === "PROPOSING" ? "bg-amber-bright" : "bg-text-faint"}`} />
          )}
          <span className="chip mono text-[10px] text-text-dim">{snap?.agent.status ?? "IDLE"}</span>
        </div>
      </div>

      {/* Action lifecycle indicator */}
      {snap?.current_action && (
        <div className="mt-3 flex items-center gap-2 border-t border-[rgba(35,42,53,0.3)] pt-3">
          <span className="label">ACTION</span>
          <div className="flex items-center gap-2 ml-auto">
            {snap.agent.status === "PROPOSING" && (
              <span className="chip warn mono">ACTION PROPOSED</span>
            )}
            {snap.agent.status === "WAITING_FOR_AUTHORIZATION" && (
              <span className="chip warn mono">WAITING FOR SENTINEL</span>
            )}
            {snap.agent.status === "WAITING_FOR_APPROVAL" && (
              <span className="chip approval mono">WAITING FOR APPROVAL</span>
            )}
            {snap.agent.status === "EXECUTING" && (
              <span className="chip allow mono">EXECUTING</span>
            )}
            {snap.agent.status === "COMPLETED" && (
              <span className="chip allow mono">COMPLETED</span>
            )}
            {snap.agent.status === "BLOCKED" && (
              <span className="chip block mono">BLOCKED</span>
            )}
            {snap.agent.status === "FAILED" && (
              <span className="chip block mono">ERROR</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}