import type { ActivityRecord, RangeKey } from '../types';
import { formatDuration, formatTime, label, Panel, StateMessage } from './common';

const RANGE_OPTIONS: [RangeKey, string][] = [['1h', 'Last hour'], ['24h', '24 hours'], ['7d', '7 days'], ['30d', '30 days']];
export function RangeSelect({ value, onChange }: { value: RangeKey; onChange: (range: RangeKey) => void }) { return <label className="range-select">Time range<select value={value} onChange={e => onChange(e.target.value as RangeKey)}>{RANGE_OPTIONS.map(([v, text]) => <option value={v} key={v}>{text}</option>)}</select></label>; }

export function calculateDurations(items: ActivityRecord[], end = Date.now()) {
  const sorted = [...items].sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime());
  return sorted.map((item, index) => ({ ...item, duration: item.duration_seconds ?? Math.max(0, ((index < sorted.length - 1 ? new Date(sorted[index + 1].ts).getTime() : Math.min(end, new Date(item.ts).getTime() + 300_000)) - new Date(item.ts).getTime()) / 1000) })).reverse();
}
export function ActivityTimeline({ items, range, loading, error, onRange, retry }: { items: ActivityRecord[]; range: RangeKey; loading: boolean; error?: string; onRange: (r: RangeKey) => void; retry: () => void }) {
  const rows = calculateDurations(items);
  return <Panel title="Activity timeline" id="timeline" actions={<RangeSelect value={range} onChange={onRange} />}>{loading ? <StateMessage kind="loading">Loading activity history…</StateMessage> : error ? <StateMessage kind="error" retry={retry}>{error}</StateMessage> : !rows.length ? <StateMessage kind="empty">No activity was recorded in this period.</StateMessage> : <ol className="timeline-list">{rows.map(row => <li key={row.id}><span className={`timeline-dot activity-bg-${row.activity.toLowerCase()}`} aria-hidden="true"/><div><strong>{label(row.activity)}</strong><span>{formatTime(row.ts)}</span></div><span className="duration">{formatDuration(row.duration)}</span></li>)}</ol>}</Panel>;
}
