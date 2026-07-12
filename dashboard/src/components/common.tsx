import type { ReactNode } from 'react';

export const formatTime = (value?: string | null) => value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : 'No update yet';
export const formatDuration = (seconds: number) => seconds < 60 ? `${Math.round(seconds)} sec` : seconds < 3600 ? `${Math.round(seconds / 60)} min` : `${(seconds / 3600).toFixed(1)} hr`;
export const label = (value: string) => value.replaceAll('_', ' ').toLowerCase().replace(/^./, c => c.toUpperCase());
export function Panel({ title, children, id, actions }: { title: string; children: ReactNode; id?: string; actions?: ReactNode }) {
  return <section className="panel" id={id} aria-labelledby={`${id || title}-title`}><header className="panel-header"><h2 id={`${id || title}-title`}>{title}</h2>{actions}</header>{children}</section>;
}
export function StateMessage({ kind, children, retry }: { kind: 'loading' | 'error' | 'empty'; children: ReactNode; retry?: () => void }) {
  return <div className={`state-message ${kind}`} role={kind === 'error' ? 'alert' : 'status'} aria-live="polite"><span aria-hidden="true">{kind === 'loading' ? '◌' : kind === 'error' ? '!' : '○'}</span><p>{children}</p>{retry && <button className="button secondary" onClick={retry}>Try again</button>}</div>;
}
