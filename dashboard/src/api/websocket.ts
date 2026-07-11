import type { WsEnvelope } from '../types';

type ConnectionState = 'connecting' | 'connected' | 'disconnected';
export class LiveSocket {
  private socket?: WebSocket; private retry?: number; private attempts = 0; private stopped = false;
  constructor(private onMessage: (message: WsEnvelope) => void, private onState: (state: ConnectionState, reconnected: boolean) => void, private url?: string) {}
  start() { this.stopped = false; this.connect(); }
  stop() { this.stopped = true; window.clearTimeout(this.retry); this.socket?.close(); this.socket = undefined; }
  private connect() {
    if (this.stopped || this.socket) return;
    const wasReconnect = this.attempts > 0;
    this.onState('connecting', false);
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(this.url || `${protocol}//${location.host}/ws`); this.socket = socket;
    socket.onopen = () => { this.attempts = 0; this.onState('connected', wasReconnect); };
    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(String(event.data)) as WsEnvelope;
        if (parsed && ['activity', 'event', 'feedback'].includes(parsed.channel) && parsed.data) this.onMessage(parsed);
      } catch { /* ignore malformed/untrusted frames */ }
    };
    socket.onerror = () => socket.close();
    socket.onclose = () => {
      if (this.socket !== socket) return; this.socket = undefined;
      if (this.stopped) return;
      this.onState('disconnected', false); this.attempts += 1;
      const delay = Math.min(30_000, 500 * 2 ** Math.min(this.attempts - 1, 6)) + Math.random() * 250;
      this.retry = window.setTimeout(() => this.connect(), delay);
    };
  }
}
