import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, Info, Send, Target, TerminalSquare } from "lucide-react";
import { useSentinel } from "../store";
import { AGENT_ACTIVE } from "../store";

const SCENARIOS = [
  { key: "safe", label: "SAFE", desc: "browse the demo site" },
  { key: "attack", label: "ATTACK", desc: "page injects forged instructions" },
  { key: "sensitive", label: "SENSITIVE", desc: "auth fields → approval gate" },
] as const;

export default function CommandBar() {
  const sessionId = useSentinel((s) => s.sessionId);
  const snap = useSentinel((s) => s.snap);
  const run = useSentinel((s) => s.run);
  const busy = useSentinel((s) => s.actionsBusy);
  const lastError = useSentinel((s) => s.lastError);
  const lastMessage = useSentinel((s) => s.lastMessage);
  const clearError = useSentinel((s) => s.clearError);
  const [task, setTask] = useState("");
  const [showExamples, setShowExamples] = useState(false);

  const running = snap ? AGENT_ACTIVE[snap.agent.status] : false;
  const disabled = busy || running || !sessionId;

  const submitTask = () => {
    const t = task.trim();
    if (!t || disabled) return;
    setTask("");
    void run({ task: t });
  };

  const exampleTasks = [
    "Update my profile email",
    "Navigate to the main article and read the second section",
    "Find all forms on the page and fill them with test data",
    "Click the login button",
    "Extract all text from the page",
    "Open the vendor site and click on the download button"
  ];

  return (
    <div className="panel p-3.5">
      <div className="flex items-center gap-2">
        <TerminalSquare className="h-4 w-4 text-amber-bright" />
        <span className="label">COMMAND — SCENARIOS</span>
        {!sessionId && !busy && <span className="chip warn mono ml-auto">session required</span>}
        <button
          onClick={() => setShowExamples(!showExamples)}
          className="mono text-[10px] text-text-faint hover:text-amber-bright transition-colors"
        >
          {showExamples ? "HIDE EXAMPLES" : "SHOW EXAMPLES"}
        </button>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {SCENARIOS.map((s) => (
          <button
            key={s.key}
            className="btn flex-1 min-w-[130px] flex-col !items-start gap-0.5 !py-2"
            disabled={disabled}
            onClick={() => void run({ scenario: s.key })}
          >
            <span className="text-[13px] font-bold tracking-[0.1em]">{s.label}</span>
            <span className="text-[10px] font-normal text-text-faint normal-case tracking-normal">{s.desc}</span>
          </button>
        ))}
      </div>

      <AnimatePresence>
        {showExamples && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-3 overflow-hidden"
          >
            <div className="rounded-lg border border-[rgba(242,184,75,0.2)] bg-[rgba(242,184,75,0.05)] p-3">
              <div className="mb-2 mono text-[10.5px] text-text-dim uppercase tracking-wide">EXAMPLE TASKS</div>
              <div className="grid grid-cols-1 gap-1.5">
                {exampleTasks.map((ex, i) => (
                  <button
                    key={i}
                    onClick={() => setTask(ex)}
                    className="text-left text-[11.5px] hover:bg-[rgba(242,184,75,0.1)] p-2 rounded transition-colors text-text-dim hover:text-amber-bright"
                  >
                    <span className="text-amber-bright mr-2">▸</span>
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="mt-3 flex gap-2">
        <div className="relative flex-1">
          <Target className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-faint" />
          <input
            className="field !pl-9"
            placeholder="or give the agent a task in natural language…"
            value={task}
            onChange={(e) => setTask(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submitTask()}
            disabled={disabled}
          />
        </div>
        <button className="btn primary" disabled={disabled || !task.trim()} onClick={submitTask}>
          <Send className="h-3.5 w-3.5" /> RUN
        </button>
      </div>

      <AnimatePresence>
        {lastError && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-2 flex items-start gap-2 overflow-hidden rounded-lg border border-[rgba(255,107,87,0.4)] bg-[rgba(255,107,87,0.08)] p-2"
          >
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-coral" />
            <span className="flex-1 text-[11.5px] text-rose-100">{lastError}</span>
            <button className="mono text-[10px] text-text-faint hover:text-text" onClick={clearError}>✕</button>
          </motion.div>
        )}
        {lastMessage && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-2 flex items-center gap-2 overflow-hidden rounded-lg border border-[rgba(94,224,214,0.3)] bg-[rgba(94,224,214,0.06)] p-2"
          >
            <Info className="h-3.5 w-3.5 shrink-0 text-cyan" />
            <span className="flex-1 text-[11.5px] text-cyan">{lastMessage}</span>
            <button className="mono text-[10px] text-text-faint hover:text-text" onClick={clearError}>✕</button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}