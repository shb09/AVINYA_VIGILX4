import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Camera, Globe, MousePointerClick, Type } from "lucide-react";
import { useSentinel } from "../store";
import { AGENT_ACTIVE } from "../store";

function trustColor(trust: string | undefined) {
  if (!trust) return "text-text-faint";
  const t = trust.toLowerCase();
  if (t.includes("untrusted")) return "text-coral";
  if (t.includes("internal")) return "text-mint";
  if (t.includes("verified")) return "text-cyan";
  return "text-amber-bright";
}

export default function BrowserStage() {
  const snap = useSentinel((s) => s.snap);
  const shot = useSentinel((s) => s.screenshot);
  const input = useSentinel((s) => s.input);
  const [hover, setHover] = useState<{ x: number; y: number } | null>(null);
  const [tool, setTool] = useState<"click" | "type">("click");
  const stageRef = useRef<HTMLDivElement>(null);

  const human = snap?.human_control ?? false;
  const busy = snap ? AGENT_ACTIVE[snap.agent.status] : false;
  const nav = snap?.browser;

  const onStageClick = (e: React.MouseEvent) => {
    if (!human || !shot || tool === "type") return;
    const rect = stageRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = Math.round(((e.clientX - rect.left) / rect.width) * shot.width);
    const y = Math.round(((e.clientY - rect.top) / rect.height) * shot.height);
    input({ type: "click", x, y });
  };

  const onMove = (e: React.MouseEvent) => {
    const rect = stageRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = Math.round(((e.clientX - rect.left) / rect.width) * (shot?.width ?? 1280));
    const y = Math.round(((e.clientY - rect.top) / rect.height) * (shot?.height ?? 840));
    setHover({ x, y });
  };

  const onOut = () => setHover(null);

  return (
    <div className="panel overflow-hidden scanline relative">
      <div className="flex items-center gap-2 border-b border-[color:var(--border)] px-3 py-2">
        <span className={`h-2 w-2 rounded-full ${nav?.status === "READY" || nav?.status === "LOADED" ? "bg-mint" : "bg-coral"} pulse-drop`} />
        <Globe className="h-3.5 w-3.5 text-text-dim" />
        <span className="mono flex-1 truncate text-[11px] text-text-dim tracking-tight">{nav?.url || "not connected to a browser"}</span>
        <span className={`chip mono ${nav ? "allow" : ""}`}>
          {nav ? "TRUST " + (nav.page_trust ?? "UNKNOWN") : "OFFLINE"}
        </span>
        <span className={`chip mono ${trustColor(nav?.page_trust || "")}`}>{nav?.host || "—"}</span>
        {human ? <span className="chip warn mono">HUMAN CONTROL</span> : <span className="mono text-[10px] text-text-faint">{nav?.status}</span>}
      </div>

      <div ref={stageRef} className="relative" onClick={onStageClick} onMouseMove={onMove} onMouseLeave={onOut}>
        <AnimatePresence mode="wait">
          {shot ? (
            <motion.img
              key="shot"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.12 }}
              src={shot.uri}
              alt="live browser"
              className="block w-full select-none"
              style={{ aspectRatio: `${shot.width} / ${shot.height}` }}
            />
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex aspect-[1280/840] items-center justify-center flex-col gap-3 text-text-faint"
            >
              <Camera className="h-8 w-8" />
              <span className="mono text-[11px] tracking-[0.2em] uppercase">Standing by — start a run to connect live browser</span>
            </motion.div>
          )}
        </AnimatePresence>

        {human && shot && (
          <div className="absolute left-1/2 top-2 z-20 flex -translate-x-1/2 items-center gap-1 rounded-lg border border-[rgba(242,184,75,0.4)] bg-black/60 px-2 py-1 backdrop-blur"
            onClick={(e) => e.stopPropagation()}>
            <button
              className={`flex items-center gap-1 rounded px-2 py-1 mono text-[10px] tracking-wide ${tool === "click" ? "bg-amber/20 text-amber-bright" : "text-text-dim hover:text-text"}`}
              onClick={() => setTool("click")}
            >
              <MousePointerClick className="h-3 w-3" /> CLICK
            </button>
            <button
              className={`flex items-center gap-1 rounded px-2 py-1 mono text-[10px] tracking-wide ${tool === "type" ? "bg-amber/20 text-amber-bright" : "text-text-dim hover:text-text"}`}
              onClick={() => setTool("type")}
            >
              <Type className="h-3 w-3" /> TYPE
            </button>
          </div>
        )}

        {human && shot && tool === "click" && hover && (
          <div
            className="pointer-events-none absolute z-10 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-amber-bright"
            style={{
              left: `${(hover.x / shot.width) * 100}%`,
              top: `${(hover.y / shot.height) * 100}%`,
              boxShadow: "0 0 12px rgba(242,184,75,0.6)",
            }}
          />
        )}

        {busy && (
          <div className="pointer-events-none absolute inset-0 z-10 flex items-start justify-center pt-3">
            <span className="chip warn mono rounded-md bg-black/60">{snap?.agent.status}…</span>
          </div>
        )}

        {!human && shot && tool === "click" && (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 flex justify-center pb-2">
            <span className="mono text-[9px] tracking-[0.2em] uppercase bg-black/50 px-2 py-0.5 rounded text-text-faint">
              observe · plan · proposal → sentinel decides
            </span>
          </div>
        )}
      </div>
    </div>
  );
}