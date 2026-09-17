import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import { NavLink } from "react-router-dom";
import { ChevronsDown, ShieldCheck } from "lucide-react";
import StatusStrip, { SessionControls } from "./StatusStrip";
import { useSentinel } from "../store";

const LINKS = [
  { to: "/", label: "Operate" },
  { to: "/story", label: "Story" },
  { to: "/security", label: "Security" },
  { to: "/provenance", label: "Provenance" },
  { to: "/audit", label: "Audit" },
  { to: "/benchmark", label: "Benchmark" },
  { to: "/settings", label: "Settings" },
] as const;

export default function TopNav() {
  const [collapsed, setCollapsed] = useState(false);
  const snap = useSentinel((s) => s.snap);

  return (
    <motion.header
      layout
      className="sticky top-0 z-40 border-b border-[color:var(--border)]"
      style={{ background: "linear-gradient(180deg, rgba(11,13,16,0.96), rgba(11,13,16,0.86))", backdropFilter: "blur(10px)" }}
    >
      <div className={`mx-auto flex items-center gap-4 px-4 transition-all ${collapsed ? "py-1.5" : "py-2.5"}`}>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="group flex items-center gap-3 rounded-lg px-1 relative"
          title={collapsed ? "Expand navigation" : "Collapse navigation"}
        >
          <motion.div
            layout
            className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-[rgba(242,184,75,0.4)]"
            style={{ background: "radial-gradient(120% 120% at 30% 20%, rgba(242,184,75,0.22), rgba(11,13,16,0.9))" }}
          >
            <ShieldCheck className="h-4.5 w-4.5 text-amber-bright" style={{ width: 18, height: 18 }} />
            <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-amber shadow-glow pulse-drop" />
          </motion.div>
          <div className="flex flex-col leading-none text-left">
            <span className="text-[15px] font-bold tracking-[0.14em] text-amber-bright">SENTINEL</span>
            <span className="text-[9px] tracking-[0.28em] uppercase text-text-faint">agent security layer</span>
          </div>
          <ChevronsDown className={`h-3.5 w-3.5 text-text-faint transition-transform ${collapsed ? "rotate-180" : ""}`} />
        </button>

        <AnimatePresence initial={false}>
          {!collapsed && (
            <motion.nav
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.18 }}
              className="flex flex-1 flex-wrap items-center gap-1 overflow-hidden"
            >
              {LINKS.map((l) => (
                <NavLink
                  key={l.to}
                  to={l.to}
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded-md text-[12.5px] font-medium tracking-wide transition-colors ${
                      isActive ? "bg-[rgba(242,184,75,0.12)] text-amber-bright border border-[rgba(242,184,75,0.25)]" : "text-text-dim hover:text-amber-bright"
                    }`
                  }
                >
                  {l.label}
                </NavLink>
              ))}
              <div className="ml-auto flex items-center gap-3">
                <SessionControls />
                <div className="hidden lg:flex h-6 w-px bg-[color:var(--border)]" />
                <StatusStrip />
              </div>
            </motion.nav>
          )}
        </AnimatePresence>

        {collapsed && (
          <div className="flex flex-1 items-center justify-end gap-3 pr-2">
            <span className="mono text-[10px] tracking-widest text-text-faint uppercase">
              {snap?.agent.status ?? "offline"} · {snap?.browser.status ?? "disconnected"}
            </span>
          </div>
        )}
      </div>
    </motion.header>
  );
}