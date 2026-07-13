import type { SystemStatus } from '../types';
import { formatTime, label } from './common';
import { CheckCircle, WarningCircle, WifiHigh, WifiSlash } from '@phosphor-icons/react';

export function StatusBar({ status, connection, stale }: { status: SystemStatus | null; connection: string; stale: boolean }) {
  const sources = status ? Object.entries(status.modality_health) : [];
  const components = status ? Object.entries(status.components).filter(([, health]) => health.status !== 'healthy') : [];
  const isOnline = connection === 'connected' && !stale;

  return (
    <section className={`flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-2xl border ${isOnline ? 'bg-emerald-50/50 border-emerald-100' : 'bg-red-50/50 border-red-100'}`} aria-label="System health">
      <div className="flex items-center gap-3">
        <div className="relative flex items-center justify-center w-10 h-10 rounded-full bg-white border border-slate-100 shadow-sm">
          {isOnline ? (
            <WifiHigh weight="bold" className="text-emerald-500 w-5 h-5 animate-pulse" />
          ) : (
            <WifiSlash weight="bold" className="text-red-500 w-5 h-5" />
          )}
        </div>
        <div className="flex flex-col">
          <strong className="text-sm text-slate-900">
            {stale ? 'Data is stale' : connection === 'connected' ? 'Live monitoring active' : connection === 'connecting' ? 'Connecting...' : 'Reconnecting...'}
          </strong>
          <span className="text-xs text-slate-500">WebSocket fusion stream</span>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {sources.map(([name, health]) => (
          <div key={name} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border bg-white ${health.status === 'online' ? 'border-slate-200' : 'border-red-200 text-red-700'}`}>
            {health.status === 'online' ? <CheckCircle weight="fill" className="text-emerald-500 w-4 h-4" /> : <WarningCircle weight="fill" className="text-red-500 w-4 h-4" />}
            <div className="flex flex-col">
              <span className="text-xs font-semibold leading-none">{label(name)}</span>
              <span className="text-[10px] text-slate-400 mt-0.5">{formatTime(health.last_update)}</span>
            </div>
          </div>
        ))}
        {components.map(([name, health]) => (
          <div key={name} className="flex items-center gap-2 px-3 py-1.5 rounded-lg border bg-red-50 border-red-200 text-red-700">
            <WarningCircle weight="fill" className="text-red-500 w-4 h-4" />
            <div className="flex flex-col">
              <span className="text-xs font-semibold leading-none">{label(name)}</span>
              <span className="text-[10px] text-red-400 mt-0.5">{health.detail || 'Service degraded'}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
