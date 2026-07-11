import type { EventRecord } from '../types';
import { formatTime, label } from './common';

export function FallAlertBanner({ event, acknowledging, onAcknowledge }: { event?: EventRecord; acknowledging: boolean; onAcknowledge: (id: number) => void }) {
  if (!event || event.acknowledged) return null;
  return <section className="fall-banner" role="alert" aria-labelledby="fall-heading">
    <div className="alert-icon" aria-hidden="true">!</div><div><p className="eyebrow">Immediate attention recommended</p><h2 id="fall-heading">{label(event.type)} detected</h2><p>Detected {formatTime(event.ts)} with {Math.round(event.confidence * 100)}% confidence. Check on the patient and follow your established response plan.</p><p className="safety-note">Acknowledging only marks this message as seen; it does not confirm the patient is safe.</p></div>
    <div className="banner-actions"><a className="button light" href="#alerts">View details</a><button className="button outline-light" disabled={acknowledging} onClick={() => onAcknowledge(event.id)}>{acknowledging ? 'Saving…' : 'Mark as seen'}</button></div>
  </section>;
}
