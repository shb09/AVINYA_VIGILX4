import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, Skull, ShieldOff } from "lucide-react";
import { useSentinel } from "../store";
import type { Threat } from "../lib/types";

function tone(sev: string) {
  return sev.toLowerCase().includes("critical") || sev.toLowerCase().includes("high")
    ? "text-coral"
    : sev.toLowerCase().includes("medium")
      ? "text-amber-bright"
      : "text-cyan";
}

export function ThreatIcon({ t }: { t: Threat }) {
  if (t.type.startsWith("INDIRECT")) return <Skull className="h-4 w-4 shrink-0 text-coral" />;
  if (t.type.startsWith("DIRECT")) return <ShieldOff className="h-4 w-4 shrink-0 text-coral" />;
  return <AlertTriangle className="h-4 w-4 shrink-0 text-amber-bright" />;
}

export default function ThreatList({ compact = false }: { compact?: boolean }) {
  const threats = useSentinel((s) => s.snap?.threats ?? []);
  if (threats.length === 0) return null;

  return (
    <div className="panel p-3" style={{ borderColor: "rgba(255,107,87,0.35)" }}>
      <div className="flex items-center gap-2">
        <Skull className="h-4 w-4 text-coral" />
        <span className="label !text-coral">{threats.length} THREAT{threats.length > 1 ? "S" : ""} CONTAINED</span>
      </div>
      <div className="mt-2 space-y-2">
        <AnimatePresence initial={false}>
          {threats.map((t: Threat) => (
            <motion.div
              key={t.type + (t.action_id ?? "")}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.16 }}
              className="rounded-lg border border-[rgba(255,107,87,0.2)] bg-[rgba(255,107,87,0.05)] p-2.5"
            >
              <div className="flex items-center gap-2">
                <ThreatIcon t={t} />
                <span className="mono text-[11px] uppercase tracking-wide text-text">{t.title}</span>
                <span className={`mono ml-auto text-[10px] uppercase ${tone(t.severity)}`}>{t.severity}</span>
              </div>
              {!compact && (
                <p className="mt-1.5 pl-6 text-[11.5px] leading-relaxed text-text-dim">{t.detail}</p>
              )}
              <div className="mt-1.5 pl-6 mono text-[10px] text-text-faint">POLICY {t.story.policy_stopped?.join(" · ") ?? "—"}</div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}