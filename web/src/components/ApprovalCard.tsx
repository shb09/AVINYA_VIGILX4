import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, Lock, X } from "lucide-react";
import { useSentinel } from "../store";
import type { PendingApproval } from "../lib/types";

function proposalLabel(action: unknown): string {
  if (!action || typeof action !== "object") return "action";
  const a = action as Record<string, unknown>;
  const t = (a.action_type as string) ?? "ACTION";
  if (t === "SUBMIT") return "submit form";
  if (t === "NAVIGATE") return `navigate → ${a.url as string}`;
  if (t === "CLICK") return `click ${a.selector as string}`;
  if (t === "FILL") return `fill ${a.selector as string}`;
  return t.toLowerCase();
}

export default function ApprovalCard() {
  const pending = useSentinel((s) => s.snap?.pending_approval);
  const approve = useSentinel((s) => s.approve);
  const actionsBusy = useSentinel((s) => s.actionsBusy);
  const [left, setLeft] = useState(0);

  const p: PendingApproval | null = pending ?? null;

  const deadline = Date.now() + (p?.expires_in ?? 0) * 1000;

  useEffect(() => {
    if (!p) return;
    const tick = () => setLeft(Math.max(0, Math.round((deadline - Date.now()) / 1000)));
    const iv = setInterval(tick, 500);
    tick();
    return () => clearInterval(iv);
  }, [p, p?.action_id]);

  return (
    <AnimatePresence>
      {p && (
        <motion.div
          initial={{ opacity: 0, y: 18, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 12, scale: 0.98 }}
          transition={{ duration: 0.22 }}
          className="panel relative overflow-hidden p-4"
          style={{ borderColor: "rgba(94,224,214,0.45)", boxShadow: "0 0 34px -8px rgba(94,224,214,0.25)" }}
        >
          <div className="absolute inset-x-0 top-0 h-0.5" style={{ background: "linear-gradient(90deg, transparent, #5EE0D6, transparent)" }} />
          <div className="flex items-center gap-2">
            <Lock className="h-4 w-4 text-cyan" />
            <span className="label !text-cyan">HUMAN APPROVAL REQUIRED</span>
            <span className="ml-auto mono text-[11px] text-cyan">⏱ {left}s</span>
          </div>

          <div className="mt-3">
            <div className="mono text-[12px] text-text-dim">
              ACTION_ID <span className="text-text">{p.action_id}</span>
            </div>
            <div className="mt-1 text-[15px] font-semibold text-text">{proposalLabel(p.proposal)}</div>
          </div>

          <div className="mt-3 space-y-1">
            {p.decision.policy_ids.map((pid) => (
              <div key={pid} className="mono text-[11px] text-cyan">▸ {pid}</div>
            ))}
            {p.decision.reasons.slice(0, 2).map((r, i) => (
              <div key={i} className="text-[12px] text-text-dim">— {r}</div>
            ))}
          </div>

          <div className="mt-4 flex gap-2">
            <button className="btn ok flex-1" onClick={() => approve(p.action_id, true)} disabled={actionsBusy}>
              <Check className="h-3.5 w-3.5" /> GRANT
            </button>
            <button className="btn danger flex-1" onClick={() => approve(p.action_id, false)} disabled={actionsBusy}>
              <X className="h-3.5 w-3.5" /> DENY
            </button>
          </div>
          <p className="mt-2 mono text-[9.5px] tracking-wide text-text-faint">DECISION IS SINGLE-USE · BOUND TO THIS ACTION · EXPIRES AUTONOMOUSLY</p>
        </motion.div>
      )}
    </AnimatePresence>
  );
}