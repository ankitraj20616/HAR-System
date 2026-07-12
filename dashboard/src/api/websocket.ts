import type { WsEnvelope } from '../types';
import { api } from './client';

type ConnectionState = 'connecting' | 'connected' | 'disconnected';
export class LiveSocket {
  private socket?: WebSocket; private retry?: number; private attempts = 0; private stopped = false;
  constructor(private onMessage: (message: WsEnvelope) => void, private onState: (state: ConnectionState, reconnected: boolean) => void, private target: 'fusion' | 'feedback', private url?: string) {}
  start() { this.stopped = false; this.connect(); }
  stop() { this.stopped = true; window.clearTimeout(this.retry); this.socket?.close(); this.socket = undefined; }
  private async connect() {
    if (this.stopped || this.socket) return;
    const wasReconnect = this.attempts > 0;
    this.onState('connecting', false);
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    let ticket: string;
    try { ticket = (await api.websocketTicket(this.target)).ticket; }
    catch { this.scheduleReconnect(); return; }
    if (this.stopped) return;
    const base = this.url || `${protocol}//${location.host}/${this.target === 'fusion' ? 'ws' : 'feedback-ws'}`;
    const socket = new WebSocket(`${base}${base.includes('?') ? '&' : '?'}ticket=${encodeURIComponent(ticket)}`); this.socket = socket;
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
      this.scheduleReconnect();
    };
  }
  private scheduleReconnect() {
    if (this.stopped) return;
    this.onState('disconnected', false); this.attempts += 1;
    const delay = Math.min(30_000, 500 * 2 ** Math.min(this.attempts - 1, 6)) + Math.random() * 250;
    this.retry = window.setTimeout(() => void this.connect(), delay);
  }
}
