import type { ReactNode } from 'react';
import { CircleNotch, WarningCircle, Info } from '@phosphor-icons/react';

export const formatTime = (value?: string | null) => value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : 'No update yet';
export const formatDuration = (seconds: number) => seconds < 60 ? `${Math.round(seconds)} sec` : seconds < 3600 ? `${Math.round(seconds / 60)} min` : `${(seconds / 3600).toFixed(1)} hr`;
export const label = (value: string) => value.replaceAll('_', ' ').toLowerCase().replace(/^./, c => c.toUpperCase());

export function Panel({ title, children, id, actions }: { title: string; children: ReactNode; id?: string; actions?: ReactNode }) {
  return (
    <section className="flex flex-col h-full" id={id} aria-labelledby={`${id || title}-title`}>
      <header className="flex items-center justify-between mb-4">
        <h3 id={`${id || title}-title`} className="text-lg font-bold tracking-tight text-slate-800">{title}</h3>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </header>
      <div className="flex-1 min-h-0 relative">
        {children}
      </div>
    </section>
  );
}

export function StateMessage({ kind, children, retry }: { kind: 'loading' | 'error' | 'empty'; children: ReactNode; retry?: () => void }) {
  return (
    <div className={`flex flex-col items-center justify-center h-full p-8 text-center rounded-2xl border ${kind === 'error' ? 'bg-red-50/50 border-red-100 text-red-600' : 'bg-slate-50/50 border-slate-100 text-slate-500'}`} role={kind === 'error' ? 'alert' : 'status'} aria-live="polite">
      {kind === 'loading' ? <CircleNotch weight="bold" className="w-8 h-8 animate-spin mb-4" /> : 
       kind === 'error' ? <WarningCircle weight="duotone" className="w-8 h-8 mb-4 text-red-500" /> : 
       <Info weight="duotone" className="w-8 h-8 mb-4 text-slate-400" />}
      <p className="font-medium text-sm max-w-[30ch] leading-relaxed">{children}</p>
      {retry && (
        <button className="mt-4 px-4 py-2 bg-white border border-slate-200 rounded-lg shadow-sm hover:bg-slate-50 text-sm font-medium transition-colors text-slate-700" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  );
}
