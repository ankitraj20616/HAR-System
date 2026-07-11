import type { SystemStatus } from '../types';
import { formatTime, label } from './common';

export function StatusBar({ status, connection, stale }: { status: SystemStatus | null; connection: string; stale: boolean }) {
  const sources = status ? Object.entries(status.modality_health) : [];
  const components = status ? Object.entries(status.components).filter(([, health]) => health.status !== 'healthy') : [];
  return <section className={`status-bar ${stale ? 'is-stale' : ''}`} aria-label="System health" aria-live="polite">
    <div className="connection"><span className={`status-dot ${connection === 'connected' && !stale ? 'online' : 'offline'}`} aria-hidden="true"/><strong>{stale ? 'Data is stale' : connection === 'connected' ? 'Live monitoring' : connection === 'connecting' ? 'Connecting…' : 'Reconnecting…'}</strong></div>
    <div className="health-list">{sources.map(([name, health]) => <div className={`health ${health.status}`} key={name}><span aria-hidden="true">{health.status === 'online' ? '✓' : '!'}</span><span><strong>{label(name)}</strong> {health.status}<small>{formatTime(health.last_update)}</small></span></div>)}{components.map(([name, health]) => <div className="health offline" key={name}><span aria-hidden="true">!</span><span><strong>{label(name)}</strong> degraded<small>{health.detail || 'Service needs attention'}</small></span></div>)}</div>
  </section>;
}
