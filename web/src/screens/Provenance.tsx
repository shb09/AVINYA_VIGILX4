import { useEffect } from "react";
import { motion } from "framer-motion";
import { GitBranch } from "lucide-react";
import { useSentinel } from "../store";
import ProvenanceView from "../components/ProvenanceView";

export default function Provenance() {
  const ensureSession = useSentinel((s) => s.ensureSession);
  const chain = useSentinel((s) => s.snap?.provenance);
  const action = useSentinel((s) => s.snap?.current_action);
  const counter = useSentinel((s) => s.snap?.executed_count);

  useEffect(() => {
    void ensureSession();
  }, [ensureSession]);

  return (
    <div className="mx-auto max-w-[1400px] px-4 py-4">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
        <div className="mb-3">
          <h1 className="flex items-center gap-2 text-[19px] font-bold tracking-[0.08em] text-text">
            <GitBranch className="h-5 w-5 text-amber-bright" /> PROVENANCE
          </h1>
          <p className="mono text-[10.5px] tracking-[0.2em] uppercase text-text-faint">
            every decision reconstructible: instruction → page state → data class → destination → policy
          </p>
        </div>

        <div className="grid grid-cols-12 gap-3">
          <div className="col-span-12 lg:col-span-7 panel overflow-hidden" style={{ minHeight: 420 }}>
            <ProvenanceView />
          </div>
          <div className="col-span-12 lg:col-span-5 space-y-3">
            {action && (
              <div className="panel p-4">
                <span className="label">CURRENT ACTION PROPOSAL</span>
                <pre className="mt-2 overflow-x-auto rounded-lg bg-black/40 p-3 mono text-[11px] leading-relaxed text-amber-bright">
{JSON.stringify(action, null, 2)}
                </pre>
              </div>
            )}
            <div className="panel p-4">
              <span className="label">RECONSTRUCTION</span>
              <ul className="mt-3 space-y-2 text-[12.5px] text-text-dim">
                <li>1 — Every action proposes with a chain: source instruction, the page it came from, the fields involved, the destination, the policy that judged it.</li>
                <li>2 — Nodes are tagged <span className="chip allow mono mx-1">INTERNAL</span>/<span className="chip block mono mx-1">UNTRUSTED</span> as observed at proposal time.</li>
                <li>3 — The executed browser call is issued against the exact sanitized payload shown, nothing more.</li>
              </ul>
              <div className="mt-3 flex gap-2">
                <span className="chip mono">EXECUTED {counter ?? 0}</span>
                <span className="chip mono">{chain ? chain.chain_id.slice(0, 18) + "…" : "NO CHAIN"}</span>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}