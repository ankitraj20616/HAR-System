import type { SystemStatus } from '../types';
import { formatTime, label, Panel, StateMessage } from './common';

export function LiveMonitor({ status, loading, error, stale, retry }: { status: SystemStatus | null; loading: boolean; error?: string; stale: boolean; retry: () => void }) {
  return <Panel title="Current activity" id="live">{loading && !status ? <StateMessage kind="loading">Loading current activity…</StateMessage> : error && !status ? <StateMessage kind="error" retry={retry}>{error}</StateMessage> : status ? <div className="live-card"><div className={`activity-symbol activity-${status.activity.toLowerCase()}`} aria-hidden="true">{status.activity === 'UNKNOWN' ? '?' : status.activity[0]}</div><div><p className="current-label">{label(status.activity)}</p><p className="confidence">Confidence <strong>{Math.round(status.confidence * 100)}%</strong></p><p className={stale ? 'stale-copy' : 'muted'}>{stale ? 'Warning: this activity may no longer be current. ' : 'Last update '}{formatTime(status.last_update)}</p></div></div> : <StateMessage kind="empty">Waiting for the first activity update.</StateMessage>}</Panel>;
}
