import type { EventsResponse, Feedback, RangeKey, SystemStatus, TimelineResponse, TrendsResponse, EventRecord } from '../types';
import type { AppRole, AuthenticatedUser } from '../types';
import { getAccessToken, refreshAccessToken } from '../auth/session';

const API_TIMEOUT_MS = 8_000;
const fusionBase = String(import.meta.env.VITE_FUSION_API_BASE || '').replace(/\/$/, '');
const feedbackBase = String(import.meta.env.VITE_FEEDBACK_API_BASE || '').replace(/\/$/, '');
export class ApiError extends Error {
  constructor(message: string, readonly status?: number) { super(message); this.name = 'ApiError'; }
}

async function request<T>(path: string, init: RequestInit = {}, signal?: AbortSignal, retried = false): Promise<T> {
  const timeout = new AbortController();
  const timer = window.setTimeout(() => timeout.abort('timeout'), API_TIMEOUT_MS);
  const combined = signal ? AbortSignal.any([signal, timeout.signal]) : timeout.signal;
  try {
    const token = getAccessToken();
    const response = await fetch(path, { ...init, signal: combined, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...init.headers } });
    if (response.status === 401 && !retried && await refreshAccessToken()) return request<T>(path, init, signal, true);
    if (!response.ok) {
      let detail = `${response.status} ${response.statusText}`;
      try { const body = await response.json() as { detail?: string }; detail = body.detail || detail; } catch { /* non-JSON error */ }
      throw new ApiError(detail, response.status);
    }
    return await response.json() as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (timeout.signal.aborted) throw new ApiError('The server took too long to respond.');
    if ((error as DOMException).name === 'AbortError') throw error;
    throw new ApiError('Unable to reach the monitoring service.');
  } finally { window.clearTimeout(timer); }
}

function bounds(period: RangeKey) {
  const ms = { '1h': 3_600_000, '24h': 86_400_000, '7d': 604_800_000, '30d': 2_592_000_000 }[period];
  const to = new Date(); const from = new Date(to.getTime() - ms);
  return new URLSearchParams({ from: from.toISOString(), to: to.toISOString(), limit: '1000' });
}

export const api = {
  me: (signal?: AbortSignal) => request<AuthenticatedUser>('/api/auth/me', {}, signal),
  websocketTicket: (target: 'fusion' | 'feedback', signal?: AbortSignal) => request<{ ticket: string; expires_in: number }>('/api/auth/ws-ticket', { method: 'POST', body: JSON.stringify({ target }) }, signal),
  updateRole: (userId: string, role: AppRole, signal?: AbortSignal) => request<{ user_id: string; role: AppRole }>(`/api/admin/users/${encodeURIComponent(userId)}/role`, { method: 'PUT', body: JSON.stringify({ role }) }, signal),
  deleteUser: (userId: string, signal?: AbortSignal) => request<{ message: string }>(`/api/admin/users/${encodeURIComponent(userId)}`, { method: 'DELETE' }, signal),
  users: (signal?: AbortSignal) => request<{ user_id: string; email: string; role: AppRole; created_at: string }[]>('/api/admin/users', {}, signal),
  status: (signal?: AbortSignal) => request<SystemStatus>(`${fusionBase}/api/status`, {}, signal),
  timeline: (period: RangeKey, signal?: AbortSignal) => request<TimelineResponse>(`${fusionBase}/api/timeline?${bounds(period)}`, {}, signal),
  events: (period: RangeKey, signal?: AbortSignal) => request<EventsResponse>(`${fusionBase}/api/events?${bounds(period)}`, {}, signal),
  activeCritical: (signal?: AbortSignal) => request<EventRecord | null>(`${fusionBase}/api/events/active-critical`, {}, signal),
  trends: (period: RangeKey, signal?: AbortSignal) => request<TrendsResponse>(`${fusionBase}/api/trends?period=${period}`, {}, signal),
  latestFeedback: (signal?: AbortSignal) => request<Feedback | null>(`${feedbackBase}/api/feedback/latest`, {}, signal),
  generateFeedback: (mode: 'feedback' | 'summary', period: RangeKey, requestId: string, signal?: AbortSignal) => request<Feedback>(`${feedbackBase}/api/feedback/generate`, { method: 'POST', body: JSON.stringify({ mode, period, request_id: requestId }) }, signal),
  acknowledge: (id: number, signal?: AbortSignal) => request<EventRecord>(`${fusionBase}/api/events/${id}/ack`, { method: 'POST' }, signal),
};
