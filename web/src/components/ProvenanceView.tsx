import { motion, AnimatePresence } from "framer-motion";
import { GitBranch, Link2 } from "lucide-react";
import { useSentinel } from "../store";
import type { ProvenanceNode } from "../lib/types";

function nodeTone(kind: string): string {
  const k = kind.toLowerCase();
  if (k.includes("request") || k.includes("command")) return "text-amber-bright";
  if (k.includes("page") || k.includes("element")) return "text-cyan";
  if (k.includes("field") || k.includes("data")) return "text-mint";
  if (k.includes("action")) return "text-text";
  return "text-text-dim";
}

export default function ProvenanceView({ compact = false }: { compact?: boolean }) {
  const chain = useSentinel((s) => s.snap?.provenance);
  const nodes = chain?.nodes ?? [];

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-2 px-3 pt-3 pb-2">
        <GitBranch className="h-3.5 w-3.5 text-amber-bright" />
        <span className="label">PROVENANCE CHAIN</span>
        {chain && (
          <span className="ml-auto mono text-[10px] text-text-faint">
            {chain.action_id.slice(0, 16)}…
          </span>
        )}
      </div>
      <div className="scroll-thin flex-1 min-h-0 overflow-y-auto px-3 pb-3">
        {nodes.length === 0 && (
          <div className="mono text-[10.5px] tracking-widest uppercase text-text-faint">
            no chain yet — proposals build a provenance chain
          </div>
        )}

        {nodes.length > 0 && (
          <div className="relative ml-2 space-y-0 pl-5" style={{ borderLeft: "1px solid #2A313D" }}>
            <AnimatePresence initial={false}>
              {nodes.map((n: ProvenanceNode, i: number) => (
                <motion.div
                  key={n.node_id}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.15, delay: i * 0.04 }}
                  className="relative pb-3"
                >
                  <span
                    className="absolute -left-[21px] top-0.5 h-2 w-2 rounded-full border border-[color:var(--border)]"
                    style={{ background: n.trust === "untrusted" ? "#FF6B57" : n.trust === "internal" ? "#7BE0A3" : "#5EE0D6" }}
                  />
                  <div className={`mono text-[10px] uppercase tracking-wide ${nodeTone(n.kind)}`}>
                    {n.kind}
                    {n.trust && (
                      <span className="text-text-faint normal-case"> · {n.trust}</span>
                    )}
                  </div>
                  <div className="mt-0.5 flex items-start gap-1.5">
                    {(n.data_class || n.detail) && (
                      <>
                        <Link2 className="mt-0.5 h-2.5 w-2.5 shrink-0 text-text-faint" />
                        <span className="text-[11.5px] leading-relaxed text-text-dim">{n.detail ?? n.data_class}</span>
                      </>
                    )}
                    {n.data_class && <span className="mono text-[10px] text-mint">{n.data_class}</span>}
                  </div>
                  {!compact && n.origin && (
                    <div className="mono mt-0.5 text-[10px] text-text-faint">origin: {n.origin}</div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}