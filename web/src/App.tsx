import { Route, Routes } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import TopNav from "./components/TopNav";
import Operate from "./screens/Operate";
import Story from "./screens/Story";
import Security from "./screens/Security";
import Provenance from "./screens/Provenance";
import Audit from "./screens/Audit";
import Benchmark from "./screens/Benchmark";
import Settings from "./screens/Settings";
import Judge from "./screens/Judge";

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <TopNav />
      <main className="flex-1 pb-10">
        <AnimatePresence mode="wait">
          <Routes>
            <Route path="/" element={<Operate />} />
            <Route path="/story" element={<Story />} />
            <Route path="/security" element={<Security />} />
            <Route path="/provenance" element={<Provenance />} />
            <Route path="/audit" element={<Audit />} />
            <Route path="/benchmark" element={<Benchmark />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/judge" element={<Judge />} />
            <Route path="*" element={<Operate />} />
          </Routes>
        </AnimatePresence>
      </main>
    </div>
  );
}