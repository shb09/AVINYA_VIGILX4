import { useEffect } from "react";
import { motion } from "framer-motion";
import { Eye, KeyRound, Lock, ShieldCheck, Unlock } from "lucide-react";
import { useSentinel } from "../store";
import ThreatList from "../components/ThreatList";

export default function Security() {
  const ensureSession = useSentinel((s) => s.ensureSession);
  const snap = useSentinel((s) => s.snap);
  useEffect(() => {
    void ensureSession();
  }, [ensureSession]);

  const entries = snap?.data?.entries ?? [];
  const canary = snap?.data?.canary ?? null;
  const failClosed = snap?.security?.fail_closed ?? true;

  return (
    <div className="mx-auto max-w-[1400px] px-4 py-4">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
        <div className="mb-3">
          <h1 className="text-[19px] font-bold tracking-[0.08em] text-text">SECURITY</h1>
          <p className="mono text-[10.5px] tracking-[0.2em] uppercase text-text-faint">
            detection · classification · redaction · containment
          </p>
        </div>

        <ThreatList />

        <div className="mt-3 grid grid-cols-12 gap-3">
          <div className="col-span-12 lg:col-span-6 panel p-4">
            <div className="flex items-center gap-2">
              <KeyRound className="h-4 w-4 text-amber-bright" />
              <span className="label">DATA REGISTRY — LIVE OBSERVED FIELDS</span>
            </div>
            {entries.length === 0 ? (
              <p className="mt-3 mono text-[11px] text-text-faint">no sensitive fields observed yet</p>
            ) : (
              <div className="mt-3 space-y-2">
                {entries.map((e, i) => (
                  <div key={i} className="flex items-center gap-3 rounded-lg border border-[rgba(94,224,214,0.18)] bg-[rgba(94,224,214,0.04)] px-3 py-2">
                    <span className="mono text-[10.5px] text-cyan">{e.data_class}</span>
                    <span className="mono text-[11px] text-text-dim">raw locked · hint {e.hint ?? "—"}</span>
                    <span className="mono ml-auto text-[10.5px] text-text-faint">{e.source}</span>
                  </div>
                ))}
              </div>
            )}
            <p className="mt-3 mono text-[10px] leading-relaxed text-text-faint">
              RAW SECRET VALUES EXIST ONLY IN THE DATA REGISTRY'S MEMORY. NOTHING SERIALIZED CONTAINS THEM. PROPOSALS CARRY A REFERENCE (ph), NOT THE VALUE.
            </p>
          </div>

          <div className="col-span-12 lg:col-span-6 space-y-3">
            <div className="panel p-4">
              <div className="flex items-center gap-2">
                <Lock className="h-4 w-4 text-coral" />
                <span className="label !text-coral">FAIL-CLOSED MODE</span>
                <span className={`chip ml-auto ${failClosed ? "block" : "ok"} mono`}>{failClosed ? "ACTIVE" : "OFF"}</span>
              </div>
              <p className="mt-2 text-[12.5px] leading-relaxed text-text-dim">
                If a proposal cannot be positively classified as safe, Sentinel refuses it. Precedence is
                <span className="mono text-[11px] mx-1 text-text">BLOCK &gt; APPROVAL &gt; ALLOW</span>.
              </p>
            </div>

            <div className="panel p-4">
              <div className="flex items-center gap-2">
                <Eye className="h-4 w-4 text-mint" />
                <span className="label">TRUST CLASSIFICATION</span>
              </div>
              <ul className="mt-3 space-y-1.5 text-[12.5px] text-text-dim">
                <li><span className="chip allow mono mr-2">INTERNAL</span>first-party demo hosts {snap?.browser.host ? `(${snap.browser.host})` : ""}</li>
                <li><span className="chip block mono mr-2">UNTRUSTED</span>`*.localhost` — supplied content; treated as hostile</li>
                <li>Every instruction the page injects is tagged <span className="mono text-[11px] text-coral">untrusted</span>.</li>
              </ul>
            </div>

            <div className="panel p-4">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-cyan" />
                <span className="label">CANARY</span>
                <span className={`chip mono ml-auto ${canary ? "block" : "ok"}`}>{canary ? "SEEDED" : "NONE"}</span>
              </div>
              <div className="mt-2 flex items-center gap-2 mono text-[11px] text-text-dim">
                <Unlock className="h-3 w-3 text-text-faint" />
                <span>{canary ?? "not seeded in this session"}</span>
              </div>
              <p className="mt-2 text-[12px] leading-relaxed text-text-faint">
                A canary token is planted in the session. If it ever appears outside the sandbox boundary — in a proposal, audit, or an outbound destination — the leak alarm fires.
              </p>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}