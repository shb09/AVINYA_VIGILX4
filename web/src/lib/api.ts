import type { AuditRecord, AppConfig, BenchmarkSummary, JudgeRun, SentinelEvent, Snapshot } from "./types";

const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<Record<string, unknown>>("/health"),

  config: () => req<AppConfig>("/config"),

  createSession: () => req<{ session_id: string; state: Snapshot }>("/session", { method: "POST" }),

  session: (sid: string) => req<Snapshot>(`/session/${sid}`),

  deleteSession: (sid: string) => req<{ ok: boolean }>(`/session/${sid}`, { method: "DELETE" }),

  events: (sid: string, after = 0) =>
    req<{ events: SentinelEvent[]; last_seq: number }>(`/session/${sid}/events?after=${after}`),

  navigate: (sid: string, url: string) =>
    req<Snapshot>(`/session/${sid}/navigate`, { method: "POST", body: JSON.stringify({ url }) }),

  runAgent: (sid: string, body: { task?: string; scenario?: string; start_url?: string; seed_canary?: boolean }) =>
    req<Snapshot>(`/session/${sid}/agent/run`, { method: "POST", body: JSON.stringify(body) }),

  stopAgent: (sid: string) => req<Snapshot>(`/session/${sid}/agent/stop`, { method: "POST" }),

  resetSession: (sid: string) => req<Snapshot>(`/session/${sid}/reset`, { method: "POST" }),

  approval: (sid: string, actionId: string, decision: boolean) =>
    req<Snapshot>(`/session/${sid}/approval`, { method: "POST", body: JSON.stringify({ action_id: actionId, decision }) }),

  control: (sid: string, mode: "take" | "release") =>
    req<Snapshot>(`/session/${sid}/control`, { method: "POST", body: JSON.stringify({ mode }) }),

  shot: (sid: string) => req<{ image: string }>(`/session/${sid}/shot`),

  snapshot: (sid: string) => req<{ elements: unknown[]; viewport: number }>(`/session/${sid}/snapshot`),

  audit: (limit = 200, sessionId?: string) =>
    req<{ records: AuditRecord[]; count: number }>(`/audit?limit=${limit}${sessionId ? `&session_id=${sessionId}` : ""}`),

  judgeRun: (sid: string, scenario: string) =>
    req<JudgeRun>(`/judge/run`, { method: "POST", body: JSON.stringify({ session_id: sid, scenario }) }),

  benchmarkRun: () => req<BenchmarkSummary>("/benchmark/run", { method: "POST" }),

  benchmarkLatest: () => req<BenchmarkSummary>("/benchmark"),
};