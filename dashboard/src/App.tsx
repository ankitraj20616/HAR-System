import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError } from './api/client';
import { LiveSocket } from './api/websocket';
import { AIFeedbackPanel } from './components/AIFeedbackPanel';
import { ActivityTimeline } from './components/ActivityTimeline';
import { AlertsLog } from './components/AlertsLog';
import { FallAlertBanner } from './components/FallAlertBanner';
import { LiveMonitor } from './components/LiveMonitor';
import { StatusBar } from './components/StatusBar';
import { TrendsPanel } from './components/TrendsPanel';
import type { ActivityRecord, EventRecord, Feedback, RangeKey, SystemStatus, TrendsResponse, WsEnvelope } from './types';

type LoadErrors = Partial<Record<'status' | 'timeline' | 'trends' | 'events' | 'feedback', string>>;
const message = (error: unknown) => error instanceof ApiError ? error.message : 'Something went wrong.';

export default function App() {
  const [range, setRange] = useState<RangeKey>('24h');
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [timeline, setTimeline] = useState<ActivityRecord[]>([]);
  const [events, setEvents] = useState<EventRecord[]>([]);
  // Safety-critical state is intentionally independent of the selected history range.
  const [criticalEvent, setCriticalEvent] = useState<EventRecord>();
  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [errors, setErrors] = useState<LoadErrors>({});
  const [loading, setLoading] = useState({ status: true, timeline: true, trends: true, events: true, feedback: true });
  const [connection, setConnection] = useState('connecting');
  const [lastMessage, setLastMessage] = useState(Date.now());
  const [now, setNow] = useState(Date.now());
  const [pendingAck, setPendingAck] = useState<number>();
  const controller = useRef<AbortController | undefined>(undefined);
  const liveRefreshTimer = useRef<number | undefined>(undefined);
  const feedbackRequest = useRef<{ key: string; id: string } | undefined>(undefined);

  const patchError = useCallback((key: keyof LoadErrors, value?: string) => setErrors(old => ({ ...old, [key]: value })), []);
  const loadStatus = useCallback(async (signal?: AbortSignal) => { setLoading(v => ({ ...v, status: true })); try { const result = await api.status(signal); setStatus(result); patchError('status'); } catch (e) { if ((e as DOMException).name !== 'AbortError') patchError('status', message(e)); } finally { setLoading(v => ({ ...v, status: false })); } }, [patchError]);
  const loadRange = useCallback(async (selected: RangeKey, signal?: AbortSignal) => {
    setLoading(v => ({ ...v, timeline: true, trends: true, events: true }));
    await Promise.all([
      api.timeline(selected, signal).then(v => { setTimeline(v.items); patchError('timeline'); }).catch(e => { if ((e as DOMException).name !== 'AbortError') patchError('timeline', message(e)); }).finally(() => setLoading(v => ({ ...v, timeline: false }))),
      api.trends(selected, signal).then(v => { setTrends(v); patchError('trends'); }).catch(e => { if ((e as DOMException).name !== 'AbortError') patchError('trends', message(e)); }).finally(() => setLoading(v => ({ ...v, trends: false }))),
      api.events(selected, signal).then(v => { setEvents(v.items); const critical = [...v.items].reverse().find(item => item.severity === 'critical' && !item.acknowledged); if (critical) setCriticalEvent(critical); patchError('events'); }).catch(e => { if ((e as DOMException).name !== 'AbortError') patchError('events', message(e)); }).finally(() => setLoading(v => ({ ...v, events: false }))),
    ]);
  }, [patchError]);
  const loadFeedback = useCallback(async (signal?: AbortSignal) => { setLoading(v => ({ ...v, feedback: true })); try { const result = await api.latestFeedback(signal); setFeedback(result); patchError('feedback'); } catch (e) { if (e instanceof ApiError && e.status === 404) { setFeedback(null); patchError('feedback'); } else if ((e as DOMException).name !== 'AbortError') patchError('feedback', message(e)); } finally { setLoading(v => ({ ...v, feedback: false })); } }, [patchError]);
  const loadCritical = useCallback(async (signal?: AbortSignal) => { try { setCriticalEvent(await api.activeCritical(signal) || undefined); } catch (e) { if ((e as DOMException).name !== 'AbortError') patchError('events', message(e)); } }, [patchError]);
  const refreshAll = useCallback((signal?: AbortSignal) => { void loadStatus(signal); void loadRange(range, signal); void loadFeedback(signal); void loadCritical(signal); }, [loadCritical, loadFeedback, loadRange, loadStatus, range]);

  useEffect(() => {
    controller.current?.abort(); const abort = new AbortController(); controller.current = abort;
    loadStatus(abort.signal); loadRange(range, abort.signal); loadFeedback(abort.signal); loadCritical(abort.signal);
    return () => abort.abort();
  }, [range, loadCritical, loadFeedback, loadRange, loadStatus]);

  useEffect(() => {
    const timer = window.setInterval(() => { setNow(Date.now()); void loadStatus(); void loadCritical(); }, 10_000);
    return () => window.clearInterval(timer);
  }, [loadCritical, loadStatus]);

  useEffect(() => {
    const onMessage = (envelope: WsEnvelope) => {
      setLastMessage(Date.now());
      if (envelope.channel === 'activity') {
        setStatus(old => old ? { ...old, activity: envelope.data.activity, confidence: envelope.data.confidence, last_update: envelope.data.ts, data_status: 'current' } : { activity: envelope.data.activity, confidence: envelope.data.confidence, last_update: envelope.data.ts, data_status: 'current', modality_health: { sensor: { status: 'offline', last_update: null }, video: { status: 'offline', last_update: null } }, components: {} });
        window.clearTimeout(liveRefreshTimer.current);
        liveRefreshTimer.current = window.setTimeout(() => void loadRange(range), 1_500);
      } else if (envelope.channel === 'event') {
        void api.events(range).then(v => setEvents(v.items)); void loadCritical();
      } else setFeedback(envelope.data);
    };
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const fusionUrl = String(import.meta.env.VITE_FUSION_WS_URL || `${protocol}//${location.host}/ws`);
    const socket = new LiveSocket(onMessage, (state, reconnected) => { setConnection(state); if (state === 'connected') setLastMessage(Date.now()); if (reconnected) refreshAll(); }, 'fusion', fusionUrl);
    socket.start(); return () => { socket.stop(); window.clearTimeout(liveRefreshTimer.current); };
  }, [loadCritical, loadRange, range, refreshAll]);

  useEffect(() => {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const feedbackUrl = String(import.meta.env.VITE_FEEDBACK_WS_URL || `${protocol}//${location.host}/feedback-ws`);
    const socket = new LiveSocket(envelope => { if (envelope.channel === 'feedback') setFeedback(envelope.data); }, (state, reconnected) => { if (state === 'connected' && reconnected) void loadFeedback(); }, 'feedback', feedbackUrl);
    socket.start(); return () => socket.stop();
  }, [loadFeedback]);

  const stale = connection !== 'connected' || status?.data_status === 'stale' || status?.data_status === 'unavailable' || (!!status?.last_update && now - new Date(status.last_update).getTime() > 20_000) || now - lastMessage > 30_000;
  const acknowledge = async (id: number) => {
    setPendingAck(id); patchError('events');
    try { const updated = await api.acknowledge(id); setEvents(items => items.map(item => item.id === id ? updated : item)); if (criticalEvent?.id === id) setCriticalEvent(undefined); }
    catch (e) { patchError('events', `Could not acknowledge alert: ${message(e)}`); }
    finally { setPendingAck(undefined); }
  };
  const generate = async (mode: 'feedback' | 'summary') => {
    setLoading(v => ({ ...v, feedback: true })); patchError('feedback');
    const key = `${mode}:${range}`;
    if (feedbackRequest.current?.key !== key) feedbackRequest.current = { key, id: globalThis.crypto?.randomUUID?.() || `${key}:${Date.now()}` };
    try { setFeedback(await api.generateFeedback(mode, range, feedbackRequest.current.id)); feedbackRequest.current = undefined; } catch (e) { patchError('feedback', message(e)); }
    finally { setLoading(v => ({ ...v, feedback: false })); }
  };

  return <>
    <header className="site-header"><div><p className="brand-mark">HAR</p><div><h1>Caregiver dashboard</h1><p>Human activity and safety monitoring</p></div></div><nav aria-label="Dashboard sections"><a href="#live">Live</a><a href="#timeline">History</a><a href="#feedback">Feedback</a><a href="#alerts">Alerts</a></nav></header>
    <StatusBar status={status} connection={connection} stale={stale}/>
    <main id="main-content"><FallAlertBanner event={criticalEvent} acknowledging={pendingAck === criticalEvent?.id} onAcknowledge={acknowledge}/><div className="dashboard-grid"><LiveMonitor status={status} loading={loading.status} error={errors.status} stale={stale} retry={() => loadStatus()}/><ActivityTimeline items={timeline} range={range} loading={loading.timeline} error={errors.timeline} onRange={setRange} retry={() => loadRange(range)}/><TrendsPanel trends={trends} range={range} loading={loading.trends} error={errors.trends} retry={() => loadRange(range)}/><AIFeedbackPanel feedback={feedback} loading={loading.feedback} error={errors.feedback} range={range} onGenerate={generate}/><AlertsLog events={events} loading={loading.events} error={errors.events} pendingId={pendingAck} onAcknowledge={acknowledge} retry={() => loadRange(range)}/></div></main>
    <footer className="site-footer">HAR is an assistive monitoring tool, not a substitute for direct supervision or medical advice.</footer>
  </>;
}
