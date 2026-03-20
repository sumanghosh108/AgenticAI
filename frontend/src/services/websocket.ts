/**
 * WebSocket Service — real-time task progress connection.
 */

import type { WSMessage } from '@/types';

type WSCallback = (msg: WSMessage) => void;

export class TaskWebSocket {
  private ws: WebSocket | null = null;
  private taskId: string;
  private callbacks: Set<WSCallback> = new Set();
  private reconnectAttempts = 0;
  private maxReconnects = 5;
  private pingInterval: ReturnType<typeof setInterval> | null = null;

  constructor(taskId: string) {
    this.taskId = taskId;
  }

  connect(): void {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws/task/${this.taskId}`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      // Start ping keepalive
      this.pingInterval = setInterval(() => {
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send('ping');
        }
      }, 30000);
    };

    this.ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        this.callbacks.forEach((cb) => cb(msg));
      } catch {
        // ignore parse errors
      }
    };

    this.ws.onclose = () => {
      if (this.pingInterval) clearInterval(this.pingInterval);
      // Auto-reconnect
      if (this.reconnectAttempts < this.maxReconnects) {
        this.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
        setTimeout(() => this.connect(), delay);
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  onMessage(callback: WSCallback): () => void {
    this.callbacks.add(callback);
    return () => this.callbacks.delete(callback);
  }

  disconnect(): void {
    this.maxReconnects = 0; // prevent reconnect
    if (this.pingInterval) clearInterval(this.pingInterval);
    this.ws?.close();
    this.ws = null;
    this.callbacks.clear();
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
