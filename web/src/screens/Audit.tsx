import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { FileSearch, RotateCcw } from "lucide-react";
import { api } from "../lib/api";
import { useSentinel } from "../store";
import type { AuditRecord } from "../lib/types";

const TONE: Record<string, string> = {
  PROPOSAL: "text-amber-bright",
  POLICY_EVALUATED: "text-cyan",
  DECISION: "text-mint",
  ALLOW: "text-mint",
  BLOCK: "text-coral",
  EXECUTION_PREVENTED: "text-coral",
  ACTION_EXECUTED: "text-text",
  THREAT_DETECTED: "text-coral",
  APPROVAL_REQUIRED: "text-cyan",
  APPROVAL_GRANTED: "text-cyan",
  APPROVAL_DENIED: "text-coral",
};

const CRITICAL = new Set(["BLOCK", "EXECUTION_PREVENTED", "THREAT_DETECTED", "APPROVAL_DENIED"]);

export default function Audit() {
  const ensureSession = useSentinel((s) => s.ensureSession);
  const sessionId = useSentinel((s) => s.sessionId);
  const [records, setRecords] = useState<AuditRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    void ensureSession();
  }, [ensureSession]);

  const load = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const data = await api.audit(500);
      setRecords(data.records);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (sessionId) void load();
  }, [sessionId, load]);

  const shown = filter === "all" ? records : records.filter((r) => (filter === "critical" ? CRITICAL.has(r.event_type) : r.event_type === filter));
  const eventTypes = Array.from(new Set(records.map((r) => r.event_type))).sort();

  return (
    <div className="mx-auto max-w-[1500px] px-4 py-4">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
        <div className="mb-3 flex items-center gap-3">
          <div>
            <h1 className="text-[19px] font-bold tracking-[0.08em] text-text">AUDIT TRAIL</h1>
            <p className="mono text-[10.5px] tracking-[0.2em] uppercase text-text-faint">
              append-only record · hydrated for secrets, canaries, tokens
            </p>
          </div>
          <div className="ml-auto flex gap-2">
            <select className="field !w-auto !py-1.5 mono text-[11px]" value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="all">ALL ({records.length})</option>
              <option value="critical">CRITICAL</option>
              {eventTypes.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <button className="btn" onClick={() => void load()} disabled={loading}>
              <RotateCcw className="h-3.5 w-3.5" /> REFRESH
            </button>
          </div>
        </div>

        <div className="panel scroll-thin overflow-hidden">
          {loading && <div className="flex items-center gap-2 p-3 mono text-[11px] text-text-faint"><FileSearch className="h-3.5 w-3.5 pulse-drop" /> reading audit log…</div>}
          {!loading && shown.length === 0 && (
            <div className="p-6 text-center mono text-[11px] tracking-widest uppercase text-text-faint">no matching audit records yet</div>
          )}
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-[color:var(--border)] text-text-faint">
                <th className="px-4 py-2 mono text-[9.5px] tracking-[0.14em] uppercase">Time</th>
                <th className="px-4 py-2 mono text-[9.5px] tracking-[0.14em] uppercase">Ref</th>
                <th className="px-4 py-2 mono text-[9.5px] tracking-[0.14em] uppercase">Event</th>
                <th className="px-4 py-2 mono text-[9.5px] tracking-[0.14em] uppercase">Detail</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((r) => (
                <tr key={r.id} className="border-b border-[rgba(35,42,53,0.35)] hover:bg-[rgba(23,27,33,0.6)]">
                  <td className="px-4 py-1.5 mono text-[10.5px] text-text-faint whitespace-nowrap">
                    {new Date(r.created * 1000).toLocaleTimeString(undefined, { hour12: false })}
                  </td>
                  <td className="px-4 py-1.5 mono text-[10.5px] text-text-faint whitespace-nowrap">
                    {r.ref ? `${String(r.ref).slice(0, 10)}…` : "—"}
                  </td>
                  <td className="px-4 py-1.5 mono text-[10.5px] uppercase tracking-wide whitespace-nowrap">
                    <span className={TONE[r.event_type] ?? "text-text-dim"}>{r.event_type}</span>
                  </td>
                  <td className="px-4 py-1.5 text-[11.5px] text-text-dim">
                    {summarize(r)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  );
}

function summarize(r: AuditRecord): string {
  const d = (r.data ?? {}) as Record<string, unknown>;
  if (r.event_type === "PROPOSAL") return `action ${String(d.action_id ?? "").slice(0, 12)}… · ${String(d.action_type ?? "")} ${String(d.url ?? d.selector ?? "")}`;
  if (r.event_type === "POLICY_EVALUATED") return `${String(d.verdict ?? "")} · ${(d.policy_ids as string[] | undefined)?.join(" + ") ?? ""}`;
  if (r.event_type === "DECISION") return `${String(d.verdict ?? "")} → action ${String(d.action_id ?? "").slice(0, 12)}…`;
  if (r.event_type === "THREAT_DETECTED") return `${String(d.type ?? "")} · ${String(d.title ?? "")}`;
  if (r.event_type === "NAVIGATED") return `→ ${String(d.url ?? "")} (${String(d.trust ?? "")})`;
  if (r.event_type === "ACTION_EXECUTED") return `${String(d.action_type ?? "")} ${String(d.selector ?? "")}`;
  const m = d.message ?? d.note ?? d.detail;
  return typeof m === "string" ? m : JSON.stringify(d).slice(0, 140);
}