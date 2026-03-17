/** WebSocket service for real-time communication with the backend. */

import { WSMessageType } from "../models";

export type WSHandler = (type: WSMessageType, data: Record<string, unknown>) => void;

export class WebSocketService {
  private ws: WebSocket | null = null;
  private handlers: Set<WSHandler> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private userId: string;

  constructor(userId: string) {
    this.userId = userId;
  }

  /** Connect to the WebSocket server. */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/${this.userId}`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log("[WS] Connected");
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data);
        const type = msg.type as WSMessageType;
        const data = msg.data ?? {};
        this.handlers.forEach((h) => h(type, data));
      } catch (err) {
        console.error("[WS] Parse error:", err);
      }
    };

    this.ws.onclose = () => {
      console.log("[WS] Disconnected — reconnecting in 3s");
      this.reconnectTimer = setTimeout(() => this.connect(), 3000);
    };

    this.ws.onerror = (err) => {
      console.error("[WS] Error:", err);
      this.ws?.close();
    };
  }

  /** Subscribe to WebSocket messages. Returns unsubscribe function. */
  subscribe(handler: WSHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  /** Send a message through the WebSocket. */
  send(type: WSMessageType, data: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }));
    } else {
      console.warn("[WS] Not connected — message dropped");
    }
  }

  /** Close the WebSocket connection. */
  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }
}
