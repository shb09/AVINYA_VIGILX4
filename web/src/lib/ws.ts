import type { SentinelEvent, Snapshot } from "./types";

export type WsHandler = {
  onSnapshot: (snap: Snapshot) => void;
  onEvent: (event: SentinelEvent) => void;
  onStatus: (status: "connecting" | "open" | "closed") => void;
  onMessage: (message: string) => void;
};

export class SentinelSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers: WsHandler;
  private reconnectDelay = 800;
  private closed = false;
  private timer: ReturnType<typeof setTimeout> | null = null;

  constructor(sessionId: string, handlers: WsHandler) {
    this.url = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/${sessionId}`;
    this.handlers = handlers;
  }

  connect() {
    this.closed = false;
    this.open();
  }

  private open() {
    this.handlers.onStatus("connecting");
    try {
      this.ws = new WebSocket(this.url);
    } catch {
      this.scheduleReconnect();
      return;
    }
    this.ws.onopen = () => {
      this.reconnectDelay = 800;
      this.handlers.onStatus("open");
      this.send({ kind: "request_state" });
    };
    this.ws.onmessage = (msg) => {
      try {
        const raw = JSON.parse(msg.data as string);
        if (raw.type === "STATE") {
          this.handlers.onSnapshot(raw.data as Snapshot);
        } else if (raw.type === "PONG" || raw.type === "MESSAGE") {
          if (raw.message) this.handlers.onMessage(raw.message);
        } else {
          this.handlers.onEvent(raw as SentinelEvent);
        }
      } catch {
        /* ignore malformed frames */
      }
    };
    this.ws.onclose = () => {
      this.handlers.onStatus("closed");
      if (!this.closed) this.scheduleReconnect();
    };
    this.ws.onerror = () => {
      try {
        this.ws?.close();
      } catch {
        /* ignore */
      }
    };
  }

  private scheduleReconnect() {
    if (this.closed) return;
    this.timer = setTimeout(() => this.open(), this.reconnectDelay);
    this.reconnectDelay = Math.min(this.reconnectDelay * 1.6, 8000);
  }

  send(payload: unknown) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }

  ping() {
    this.send({ kind: "ping" });
  }

  requestState() {
    this.send({ kind: "request_state" });
  }

  input(payload: Record<string, unknown>) {
    this.send({ kind: "input", payload });
  }

  close() {
    this.closed = true;
    if (this.timer) clearTimeout(this.timer);
    this.ws?.close();
  }
}