export type Activity = 'WALKING' | 'SITTING' | 'STANDING' | 'LYING' | 'EXERCISING' | 'UNKNOWN';
export type Severity = 'info' | 'warning' | 'critical';
export type RangeKey = '1h' | '24h' | '7d' | '30d';

export interface ModalityHealth { status: 'online' | 'offline'; last_update: string | null }
export interface ComponentHealth { status: 'healthy' | 'degraded'; detail?: string | null }
export interface SystemStatus {
  activity: Activity; confidence: number; last_update: string | null;
  data_status?: 'current' | 'stale' | 'unavailable';
  modality_health: Record<'sensor' | 'video', ModalityHealth>;
  components: Record<string, ComponentHealth>;
}
export interface ActivityRecord { id: number; ts: string; activity: Activity; confidence: number; duration_seconds?: number; sensor_label?: Activity | null; video_label?: Activity | null }
export interface EventRecord { id: number; ts: string; type: 'FALL' | 'INACTIVITY' | 'ABNORMAL_PATTERN'; severity: Severity; confidence: number; evidence: Record<string, unknown>; acknowledged: boolean }
export interface TrendBucket { activity: Activity; count: number; duration_seconds: number }
export interface TrendsResponse { period: RangeKey; from: string; to: string; activities: TrendBucket[]; total_duration_seconds: number }
export interface Feedback { id?: number; ts: string; mode: 'alert' | 'feedback' | 'summary'; headline: string; detail: string; severity: Severity; recommendations: string[]; disclaimer: string; fallback?: boolean }
export interface TimelineResponse { items: ActivityRecord[]; count: number }
export interface EventsResponse { items: EventRecord[]; count: number }
export type WsEnvelope = { channel: 'activity'; data: { ts: string; activity: Activity; confidence: number } } | { channel: 'event'; data: EventRecord } | { channel: 'feedback'; data: Feedback };
