import { useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import BrowserStage from "../components/BrowserStage";
import CommandBar from "../components/CommandBar";
import DecisionPanel from "../components/DecisionPanel";
import ApprovalCard from "../components/ApprovalCard";
import EventStream from "../components/EventStream";
import ProvenanceView from "../components/ProvenanceView";
import ThreatList from "../components/ThreatList";
import { useSentinel } from "../store";

export default function Operate() {
  const ensureSession = useSentinel((s) => s.ensureSession);
  const sessionId = useSentinel((s) => s.sessionId);
  const wsStatus = useSentinel((s) => s.wsStatus);
  const snap = useSentinel((s) => s.snap);

  useEffect(() => {
    void ensureSession();
  }, [ensureSession]);

  const mounted = useMemo(() => Date.now(), []);

  const goal = snap?.agent.task ?? null;
  const narrative = snap?.narrative ?? null;
  const planner = snap?.agent.planner ?? "local fixture planner";

  return (
    <div className="mx-auto max-w-[1600px] px-4 py-4">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
        <div className="mb-3 flex items-center gap-3">
          <div>
            <h1 className="text-[19px] font-bold tracking-[0.08em] text-text">OPERATE</h1>
            <p className="mono text-[10.5px] tracking-[0.2em] uppercase text-text-faint">
              the agent proposes · sentinel decides · the browser executes
            </p>
          </div>
          {wsStatus !== "open" && (
            <span className="chip warn mono ml-auto">{wsStatus === "connecting" ? "connecting browser session…" : "session offline"}</span>
          )}
          {mounted > 0 && !sessionId && (
            <span className="chip block mono ml-auto">no session — start to boot browser</span>
          )}
        </div>

        {goal && <GoalBanner task={goal} planner={planner} narrative={narrative} />}

        <div className="mt-3 grid grid-cols-12 gap-3">
          <div className="col-span-12 xl:col-span-8 space-y-3">
            <BrowserStage />
            {snap?.pending_approval && <ApprovalCard />}
            {snap?.threats && snap.threats.length > 0 && <ThreatList />}
            <CommandBar />
          </div>
          <div className="col-span-12 xl:col-span-4 space-y-3">
            <DecisionPanel />
            <div className="panel h-[300px] overflow-hidden">
              <ProvenanceView />
            </div>
            <div className="panel h-[300px] overflow-hidden">
              <EventStream />
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

function GoalBanner({ task, planner, narrative }: { task: string; planner: string; narrative: string | null }) {
  return (
    <div className="panel-tight flex flex-wrap items-center gap-3 px-4 py-2.5">
      <span className="chip warn mono">GOAL</span>
      <span className="text-[14px] text-text">{task}</span>
      <span className="chip mono">{planner}</span>
      {narrative && <span className="mono ml-auto text-[10.5px] text-text-dim">{narrative}</span>}
    </div>
  );
}