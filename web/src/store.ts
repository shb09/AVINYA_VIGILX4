import { create } from "zustand";
import { api } from "./lib/api";
import { SentinelSocket } from "./lib/ws";
import type { SentinelEvent, Snapshot } from "./lib/types";

const MAX_EVENTS = 500;

interface SentinelState {
  sessionId: string | null;
  snap: Snapshot | null;
  events: SentinelEvent[];
  screenshot: { uri: string; width: number; height: number } | null;
  wsStatus: "connecting" | "open" | "closed";
  lastMessage: string | null;
  lastError: string | null;
  actionsBusy: boolean;

  ensureSession: (force?: boolean) => Promise<string | null>;
  disposeSession: () => void;
  run: (opts: { scenario?: string; task?: string }) => Promise<void>;
  stop: () => Promise<void>;
  reset: () => Promise<void>;
  approve: (actionId: string, decision: boolean) => Promise<void>;
  takeControl: () => Promise<void>;
  releaseControl: () => Promise<void>;
  navigate: (url: string) => Promise<void>;
  input: (payload: Record<string, unknown>) => void;
  refresh: () => Promise<void>;
  clearError: () => void;
}

let socket: SentinelSocket | null = null;

export const useSentinel = create<SentinelState>((set, get) => ({
  sessionId: null,
  snap: null,
  events: [],
  screenshot: null,
  wsStatus: "closed",
  lastMessage: null,
  lastError: null,
  actionsBusy: false,

  ensureSession: async (force = false) => {
    const state = get();
    if (state.sessionId && !force) return state.sessionId;

    set({ lastError: null });
    try {
      const { session_id } = await api.createSession();
      set({ sessionId: session_id, actionsBusy: true });
      await get().refresh();
      set({ actionsBusy: false });

      socket?.close();
      socket = new SentinelSocket(session_id, {
        onSnapshot: (snap) => set({ snap, lastError: null }),
        onEvent: (event) => {
          if (event.type === "SCREENSHOT") {
            const img = event.data as { image?: string; width?: number; height?: number };
            if (img.image) set({ screenshot: { uri: `data:image/jpeg;base64,${img.image}`, width: img.width ?? 1280, height: img.height ?? 840 } });
            return;
          }
          if (event.type === "BROWSER_ERROR" || event.type === "ACTION_FAILED") {
            set({ lastError: (event.data as { message?: string; note?: string })?.message ?? (event.data as { note?: string })?.note ?? "browser error" });
          }
          set((s) => ({ events: [...s.events, event].slice(-MAX_EVENTS) }));
        },
        onStatus: (wsStatus) => set({ wsStatus }),
        onMessage: (msg) => set({ lastMessage: msg }),
      });
      socket.connect();
      return session_id;
    } catch (err) {
      set({ lastError: err instanceof Error ? err.message : String(err) });
      return null;
    }
  },

  disposeSession: () => {
    socket?.close();
    socket = null;
    set({ sessionId: null, snap: null, events: [], screenshot: null, wsStatus: "closed" });
  },

  run: async (opts) => {
    const sid = get().sessionId;
    if (!sid) return;
    set({ actionsBusy: true, lastError: null });
    try {
      await api.runAgent(sid, opts);
      socket?.requestState();
      await get().refresh();
    } catch (err) {
      set({ lastError: err instanceof Error ? err.message : String(err) });
    } finally {
      set({ actionsBusy: false });
    }
  },

  stop: async () => {
    const sid = get().sessionId;
    if (!sid) return;
    set({ actionsBusy: true });
    try {
      await api.stopAgent(sid);
      socket?.requestState();
      await get().refresh();
    } catch (err) {
      set({ lastError: err instanceof Error ? err.message : String(err) });
    } finally {
      set({ actionsBusy: false });
    }
  },

  reset: async () => {
    const sid = get().sessionId;
    if (!sid) return;
    set({ actionsBusy: true, events: [], screenshot: null });
    try {
      await api.resetSession(sid);
      socket?.requestState();
      await get().refresh();
    } catch (err) {
      set({ lastError: err instanceof Error ? err.message : String(err) });
    } finally {
      set({ actionsBusy: false });
    }
  },

  approve: async (actionId, decision) => {
    const sid = get().sessionId;
    if (!sid) return;
    try {
      await api.approval(sid, actionId, decision);
      socket?.requestState();
      await get().refresh();
    } catch (err) {
      set({ lastError: err instanceof Error ? err.message : String(err) });
    }
  },

  takeControl: async () => {
    const sid = get().sessionId;
    if (!sid) return;
    await api.control(sid, "take");
    socket?.requestState();
    await get().refresh();
  },

  releaseControl: async () => {
    const sid = get().sessionId;
    if (!sid) return;
    await api.control(sid, "release");
    socket?.requestState();
    await get().refresh();
  },

  navigate: async (url) => {
    const sid = get().sessionId;
    if (!sid) return;
    await api.navigate(sid, url);
    socket?.requestState();
    await get().refresh();
  },

  input: (payload) => socket?.input(payload),

  refresh: async () => {
    const sid = get().sessionId;
    if (!sid) return;
    try {
      const snap = await api.session(sid);
      set({ snap });
      socket?.requestState();
    } catch (err) {
      set({ lastError: err instanceof Error ? err.message : String(err) });
    }
  },

  clearError: () => set({ lastError: null, lastMessage: null }),
}));

export const AGENT_ACTIVE: Record<string, boolean> = {
  OBSERVING: true,
  PLANNING: true,
  PROPOSING: true,
  WAITING_FOR_AUTHORIZATION: true,
  WAITING_FOR_APPROVAL: true,
  EXECUTING: true,
  PAUSED: true,
};

export const TERMINAL_AGENT = new Set(["COMPLETED", "BLOCKED", "FAILED", "STOPPED"]);