import { motion } from "framer-motion";
import { Activity, Power, RotateCcw, UserPlus, UserMinus, Play } from "lucide-react";
import { useSentinel } from "../store";
import { AGENT_ACTIVE } from "../store";
import type { AgentStatus, BrowserStatus, Verdict } from "../lib/types";

function dot(status: string, fine: string) {
  return <span className={`inline-block h-1.5 w-1.5 rounded-full ${status === fine ? "bg-mint shadow-[0_0_8px_rgba(123,224,163,0.8)]" : "bg-coral"}`} />;
}

export default function StatusStrip() {
  const snap = useSentinel((s) => s.snap);
  const wsStatus = useSentinel((s) => s.wsStatus);
  const sessionId = useSentinel((s) => s.sessionId);
  const ensureSession = useSentinel((s) => s.ensureSession);
  const actionsBusy = useSentinel((s) => s.actionsBusy);

  const browser: BrowserStatus = snap?.browser.status ?? "DISCONNECTED";
  const agent: AgentStatus = snap?.agent.status ?? "IDLE";
  const verdict: Verdict | undefined = snap?.security?.verdict;

  return (
    <div className="flex items-center gap-3 pl-3 mono text-[11px] text-text-dim">
      <span className="hidden xl:inline-flex items-center gap-1.5">
        {dot(browser, "READY")}
        <span>BROWSER {browser}</span>
      </span>
      <span className="hidden lg:inline-flex items-center gap-1.5">
        {dot(agent, "IDLE")}
        <span>AGENT {agent}</span>
      </span>
      <span className="hidden md:inline-flex items-center gap-1.5">
        {AGENT_ACTIVE[agent] ? (
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-pulse pulse-drop" />
        ) : (
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-cyan" />
        )}
        <span className={AGENT_ACTIVE[agent] ? "" : "text-text-faint"}>WS {wsStatus.toUpperCase()}</span>
      </span>
      {verdict && !AGENT_ACTIVE[agent] && (
        <span className="hidden sm:inline chip" data-variant={verdict}>
          {verdict}
        </span>
      )}
      {sessionId ? (
        <span className="hidden 2xl:inline-flex items-center gap-1.5 text-text-faint" title="Session">
          <Activity className="h-3 w-3" />
          {sessionId}
        </span>
      ) : (
        <button
          className="inline-flex items-center gap-1.5 hover:text-amber-bright transition-colors"
          onClick={() => ensureSession()}
          disabled={actionsBusy}
        >
          <Power className="h-3 w-3" /> START
        </button>
      )}
    </div>
  );
}

export function SessionControls() {
  const sessionId = useSentinel((s) => s.sessionId);
  const snap = useSentinel((s) => s.snap);
  const ensureSession = useSentinel((s) => s.ensureSession);
  const stop = useSentinel((s) => s.stop);
  const reset = useSentinel((s) => s.reset);
  const takeControl = useSentinel((s) => s.takeControl);
  const releaseControl = useSentinel((s) => s.releaseControl);
  const actionsBusy = useSentinel((s) => s.actionsBusy);

  if (!sessionId) return null;
  const running = snap ? AGENT_ACTIVE[snap.agent.status] : false;
  const human = snap?.human_control ?? false;

  return (
    <motion.div layout className="flex items-center gap-2">
      {running ? (
        <button className="btn danger" onClick={() => stop()} disabled={actionsBusy}>
          <RotateCcw className="h-3.5 w-3.5" /> STOP
        </button>
      ) : (
        <button className="btn" onClick={() => ensureSession(true)} disabled={actionsBusy} title="Reset session">
          <Play className="h-3.5 w-3.5" /> NEW
        </button>
      )}
      <button className="btn" onClick={() => reset()} disabled={actionsBusy} title="Reset session">
        <RotateCcw className="h-3.5 w-3.5" />
      </button>
      {human ? (
        <button className="btn ok" onClick={() => releaseControl()} disabled={actionsBusy}>
          <UserMinus className="h-3.5 w-3.5" /> CONTROL
        </button>
      ) : (
        <button className="btn" onClick={() => takeControl()} disabled={actionsBusy || running}>
          <UserPlus className="h-3.5 w-3.5" /> INTERVENE
        </button>
      )}
    </motion.div>
  );
}