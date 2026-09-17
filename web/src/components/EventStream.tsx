import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Terminal, AlertCircle, Check, X, Clock, Activity } from "lucide-react";
import { useSentinel } from "../store";
import type { SentinelEvent } from "../lib/types";

const EVENT_TONE: Record<string, string> = {
  PROPOSAL: "text-amber-bright",
  POLICY_EVALUATED: "text-cyan",
  DECISION: "text-mint",
  ALLOW: "text-mint",
  APPROVAL_REQUIRED: "text-cyan",
  APPROVAL_GRANTED: "text-cyan",
  APPROVAL_DENIED: "text-coral",
  BLOCK: "text-coral",
  EXECUTION_PREVENTED: "text-coral",
  ACTION_EXECUTED: "text-text",
  ACTION_FAILED: "text-coral",
  BROWSER_ERROR: "text-coral",
  THREAT_DETECTED: "text-coral",
  NAVIGATED: "text-text-dim",
  AGENT_STATUS: "text-text-dim",
  JOURNEY: "text-text-faint",
};

const EVENT_ICON: Record<string, any> = {
  PROPOSAL: Activity,
  POLICY_EVALUATED: AlertCircle,
  DECISION: Check,
  ALLOW: Check,
  APPROVAL_REQUIRED: Clock,
  APPROVAL_GRANTED: Check,
  APPROVAL_DENIED: X,
  BLOCK: X,
  EXECUTION_PREVENTED: X,
  ACTION_EXECUTED: Check,
  ACTION_FAILED: AlertCircle,
  BROWSER_ERROR: AlertCircle,
  THREAT_DETECTED: AlertCircle,
  NAVIGATED: Activity,
  AGENT_STATUS: Activity,
  JOURNEY: Clock,
};

export default function EventStream({ compact = false, limit = 60 }: { compact?: boolean; limit?: number }) {
  const events = useSentinel((s) => s.events);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ref.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, [events.length]);

  const shown = events.slice(-limit).reverse();

  const getEventSubtitle = (ev: SentinelEvent): string => {
    const d = ev.data as Record<string, unknown>;
    switch (ev.type) {
      case "ACTION_PROPOSED":
        return `Action: ${d.action_id || "unknown"}`;
      case "POLICY_EVALUATED":
        return `Verdict: ${d.verdict || "unknown"}`;
      case "DECISION":
        return `Decision: ${d.verdict || "unknown"} for ${d.action_id || "unknown"}`;
      case "THREAT_DETECTED":
        return `${d.type || "threat"}: ${d.title || ""}`;
      case "NAVIGATED":
        return `To: ${d.url || "unknown"}`;
      case "ACTION_EXECUTED":
        return `${d.action_type || "action"}`;
      case "AGENT_STATUS":
        return `Agent status: ${d.status || "unknown"}`;
      default:
        return ev.message || "";
    }
  };

  const formatEventTime = (created: number | undefined): string => {
    if (!created) return "";
    const date = new Date(created * 1000);
    return date.toLocaleTimeString(undefined, { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-2 px-3 pt-3 pb-2">
        <Terminal className="h-3.5 w-3.5 text-amber-bright" />
        <span className="label">EVENT STREAM</span>
        <span className="ml-auto mono text-[10px] text-text-faint">{events.length} EVENTS</span>
        {events.length > 0 && (
          <button
            onClick={() => {}}
            className="text-[10px] text-text-faint hover:text-amber-bright transition-colors"
          >
            CLEAR
          </button>
        )}
      </div>
      <div ref={ref} className="scroll-thin flex-1 min-h-0 overflow-y-auto px-3 pb-3 space-y-2">
        <AnimatePresence initial={false}>
          {shown.map((ev: SentinelEvent) => {
            const Icon = EVENT_ICON[ev.type] || Activity;
            const iconColor = EVENT_TONE[ev.type] || "text-text-dim";

            return (
              <motion.div
                key={ev.seq}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.15 }}
                className="flex gap-3 p-2 rounded-lg hover:bg-[rgba(242,184,75,0.06)] transition-colors"
              >
                <span className="mono w-16 shrink-0 text-[10px] text-text-faint leading-5 flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {formatEventTime(ev.created)}
                </span>
                <div className="flex-shrink-0 h-6 w-6 rounded-full bg-[rgba(35,42,53,0.6)] flex items-center justify-center">
                  <Icon className={`h-3.5 w-3.5 ${iconColor}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`mono text-[10.5px] uppercase tracking-wide ${iconColor}`}>
                      {ev.type}
                    </span>
                    {ev.ref && (
                      <span className="mono text-[9px] text-text-faint">
                        REF: {String(ev.ref).slice(0, 8)}...
                      </span>
                    )}
                  </div>
                  <div className="text-[12px] leading-relaxed text-text-dim">
                    {getEventSubtitle(ev)}
                  </div>
                  {ev.message && !compact && (
                    <div className="mt-1.5 pl-2 border-l-2 border-[rgba(242,184,75,0.2)]">
                      <p className="text-[11px] text-text-faint italic">
                        {ev.message}
                      </p>
                    </div>
                  )}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
        {shown.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 text-text-faint">
            <Terminal className="h-8 w-8 mb-2" />
            <div className="mono text-[11px] tracking-widest uppercase">awaiting events…</div>
            <div className="mono text-[10px] mt-2 text-text-dim">Events will appear here as the Sentinel pipeline runs</div>
          </div>
        )}
      </div>
    </div>
  );
}