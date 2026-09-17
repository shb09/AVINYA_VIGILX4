import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Terminal } from "lucide-react";
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

export default function EventStream({ compact = false, limit = 60 }: { compact?: boolean; limit?: number }) {
  const events = useSentinel((s) => s.events);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ref.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, [events.length]);

  const shown = events.slice(-limit).reverse();

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-2 px-3 pt-3 pb-2">
        <Terminal className="h-3.5 w-3.5 text-amber-bright" />
        <span className="label">EVENT STREAM</span>
        <span className="ml-auto mono text-[10px] text-text-faint">{events.length} EVENTS</span>
      </div>
      <div ref={ref} className="scroll-thin flex-1 min-h-0 overflow-y-auto px-3 pb-3 space-y-1">
        <AnimatePresence initial={false}>
          {shown.map((ev: SentinelEvent) => (
            <motion.div
              key={ev.seq}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.12 }}
              className="flex gap-2 border-b border-[rgba(35,42,53,0.4)] py-1"
            >
              <span className="mono w-10 shrink-0 text-[9.5px] text-text-faint leading-5">
                {String(ev.seq).slice(-4)}
              </span>
              <span className={`mono w-36 shrink-0 text-[10.5px] tracking-wide leading-5 uppercase ${EVENT_TONE[ev.type] ?? "text-text-dim"}`}>
                {ev.type}
              </span>
              {ev.message && (
                <span className={`text-[11.5px] leading-5 text-text-dim ${compact ? "truncate" : "line-clamp-2"}`}>
                  {ev.message}
                </span>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
        {shown.length === 0 && (
          <div className="mono text-[10.5px] tracking-widest uppercase text-text-faint pt-2">awaiting events…</div>
        )}
      </div>
    </div>
  );
}