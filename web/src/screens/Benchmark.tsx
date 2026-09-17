import { useState } from "react";
import { motion } from "framer-motion";
import { Activity, Gauge, Play, ShieldOff } from "lucide-react";
import { api } from "../lib/api";
import { useSentinel } from "../store";
import type { BenchmarkSummary } from "../lib/types";

const SCENARIO_TONE: Record<string, string> = {
  safe: "text-mint",
  attack: "text-coral",
  sensitive: "text-cyan",
};

export default function Benchmark() {
  const sessionId = useSentinel((s) => s.sessionId);
  const [result, setResult] = useState<BenchmarkSummary | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      const r = await api.benchmarkRun();
      setResult(r);
      const latest = await api.benchmarkLatest();
      setResult(latest);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="mx-auto max-w-[1400px] px-4 py-4">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
        <div className="mb-3 flex items-center gap-3">
          <div>
            <h1 className="flex items-center gap-2 text-[19px] font-bold tracking-[0.08em] text-text">
              <Gauge className="h-5 w-5 text-amber-bright" /> BENCHMARK
            </h1>
            <p className="mono text-[10.5px] tracking-[0.2em] uppercase text-text-faint">
              real browser, real pages, full scenario matrix — is it still safe?
            </p>
          </div>
          <button className="btn primary ml-auto" onClick={() => void run()} disabled={running || !sessionId}>
            {running ? <Activity className="h-3.5 w-3.5 pulse-drop" /> : <Play className="h-3.5 w-3.5" />}
            {running ? "RUNNING LIVE CASES…" : "RUN BENCHMARK"}
          </button>
        </div>

        {error && (
          <div className="panel mb-3 p-3 mono text-[11px] text-coral" style={{ borderColor: "rgba(255,107,87,0.4)" }}>
            BENCHMARK ERROR — {error}
          </div>
        )}

        {!result && !running && (
          <div className="panel flex aspect-video max-h-[340px] items-center justify-center text-text-faint">
            <span className="mono text-[11px] tracking-[0.2em] uppercase">no benchmark run yet — each case boots the browser, runs the scenario, and checks the audit trail for leaks</span>
          </div>
        )}

        {result && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <Metric label="RUN" value={`#${result.run_id}`} sub={`${result.total_cases} cases`} />
              <Metric label="ELAPSED" value={`${result.elapsed_seconds.toFixed(1)}s`} sub="wall clock" />
              <Metric label="SCENARIOS" value={String(Object.keys(result.scenarios).length)} sub={Object.keys(result.scenarios).join(" / ")} />
              <Metric
                label="LEAKS"
                value={String(result.metrics.total_secret_leaks ?? 0)}
                sub="across all boundaries"
                danger={(result.metrics.total_secret_leaks ?? 0) > 0}
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
              {Object.entries(result.scenarios)
                .map(([name, m]) => ({ name, m }))
                .map(({ name, m }) => (
                  <div key={name} className="panel p-4">
                    <div className="flex items-center gap-2">
                      <span className={`mono text-[12px] uppercase tracking-[0.14em] ${SCENARIO_TONE[name] ?? "text-text"}`}>{name}</span>
                      <span className="chip mono ml-auto">{m.count} CASES</span>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-[12px] text-text-dim">
                      <Stat k="ALLOWED" v={m.allows ?? 0} />
                      <Stat k="COMPLETED" v={m.completed ?? 0} />
                      <Stat k="BLOCKED" v={m.blocked ?? 0} />
                      <Stat k="EXECUTION PREVENTED" v={m.prevented ?? 0} />
                      <Stat k="APPROVALS" v={m.approvals ?? 0} />
                      <Stat k="APPROVED EXECUTED" v={m.approved_executions ?? 0} />
                    </div>
                  </div>
                ))}
            </div>

            <div className="panel p-4">
              <div className="flex items-center gap-2">
                <ShieldOff className="h-4 w-4 text-coral" />
                <span className="label !text-coral">CANARY / SECRET LEAK CHECKS — PER CASE</span>
              </div>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-[color:var(--border)] text-text-faint">
                      <th className="py-2 pr-3 mono text-[9.5px] uppercase">Run</th>
                      <th className="py-2 pr-3 mono text-[9.5px] uppercase">Scenario</th>
                      <th className="py-2 pr-3 mono text-[9.5px] uppercase">Terminal</th>
                      <th className="py-2 pr-3 mono text-[9.5px] uppercase">Allow</th>
                      <th className="py-2 pr-3 mono text-[9.5px] uppercase">Blocked</th>
                      <th className="py-2 pr-3 mono text-[9.5px] uppercase">Prevented</th>
                      <th className="py-2 pr-3 mono text-[9.5px] uppercase">Check</th>
                      <th className="py-2 pr-3 mono text-[9.5px] uppercase">Checks</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.cases.map((c, i) => (
                      <tr key={i} className="border-b border-[rgba(35,42,53,0.3)]">
                        <td className="py-2 pr-3 mono text-[11px] text-text-faint">#{i + 1}</td>
                        <td className={`py-2 pr-3 mono text-[11px] uppercase ${SCENARIO_TONE[c.scenario] ?? ""}`}>{c.scenario}</td>
                        <td className="py-2 pr-3 mono text-[11px] text-text-dim">{c.terminal}</td>
                        <td className="py-2 pr-3 mono text-[11px] text-mint">{c.allows}</td>
                        <td className="py-2 pr-3 mono text-[11px] text-text-dim">{c.blocked ? "YES" : "no"}</td>
                        <td className="py-2 pr-3 mono text-[11px] text-coral">{c.prevented ? "YES" : "no"}</td>
                        <td className="py-2 pr-3 mono text-[11px] text-amber-bright">{c.leak_checks}</td>
                        <td className="py-2 pr-3 mono text-[11px] text-text-dim">{c.leaks.length ? "✗ LEAKS" : "✓"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
}

function Metric({ label, value, sub, danger }: { label: string; value: string; sub: string; danger?: boolean }) {
  return (
    <div className={`panel p-4 ${danger ? "!border-[rgba(255,107,87,0.5)]" : ""}`}>
      <span className="label">{label}</span>
      <div className={`mt-2 text-[26px] font-bold mono ${danger ? "text-coral" : "text-amber-bright"}`}>{value}</div>
      <div className="mono text-[10.5px] text-text-faint">{sub}</div>
    </div>
  );
}

function Stat({ k, v }: { k: string; v: number }) {
  return (
    <div className="flex items-center justify-between rounded-md bg-black/30 px-2.5 py-1.5">
      <span className="mono text-[9.5px] uppercase tracking-wide text-text-faint">{k}</span>
      <span className="mono text-[12px] text-text">{v}</span>
    </div>
  );
}