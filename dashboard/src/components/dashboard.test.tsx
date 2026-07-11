import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { calculateDurations } from './ActivityTimeline';
import { ActivityTimeline } from './ActivityTimeline';
import { AIFeedbackPanel } from './AIFeedbackPanel';
import { AlertsLog } from './AlertsLog';
import { FallAlertBanner } from './FallAlertBanner';
import { StatusBar } from './StatusBar';
import type { ActivityRecord, EventRecord, SystemStatus } from '../types';

const status: SystemStatus = {
  activity: 'WALKING', confidence: .91, last_update: '2026-07-11T10:00:00Z', data_status: 'current',
  modality_health: { sensor: { status: 'online', last_update: '2026-07-11T10:00:00Z' }, video: { status: 'offline', last_update: null } }, components: {},
};

describe('caregiver states', () => {
  it('does not hide a degraded modality behind overall live state', () => {
    render(<StatusBar status={status} connection="connected" stale={false}/>);
    expect(screen.getByText(/Live monitoring/)).toBeInTheDocument();
    expect(screen.getByText('Video')).toHaveTextContent('Video');
    expect(screen.getByText(/offline/)).toBeInTheDocument();
  });

  it('announces a critical event and explains acknowledgement semantics', () => {
    const acknowledge = vi.fn();
    const event: EventRecord = { id: 7, ts: '2026-07-11T10:00:00Z', type: 'FALL', severity: 'critical', confidence: .94, evidence: {}, acknowledged: false };
    render(<FallAlertBanner event={event} acknowledging={false} onAcknowledge={acknowledge}/>);
    expect(screen.getByRole('alert')).toHaveTextContent('Fall detected');
    expect(screen.getByText(/does not confirm the patient is safe/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Mark as seen' }));
    expect(acknowledge).toHaveBeenCalledWith(7);
  });

  it('uses server durations and bounds a final client-computed interval', () => {
    const items: ActivityRecord[] = [
      { id: 1, ts: '2026-07-11T10:00:00Z', activity: 'WALKING', confidence: .8, duration_seconds: 42 },
      { id: 2, ts: '2026-07-11T10:10:00Z', activity: 'SITTING', confidence: .9 },
    ];
    const result = calculateDurations(items, new Date('2026-07-11T11:00:00Z').getTime());
    expect(result.find(row => row.id === 1)?.duration).toBe(42);
    expect(result.find(row => row.id === 2)?.duration).toBe(300);
  });

  it('announces stale, loading, empty, error, and acknowledged states', () => {
    const { rerender } = render(<StatusBar status={status} connection="disconnected" stale={true}/>);
    expect(screen.getByText('Data is stale')).toBeInTheDocument();

    rerender(<ActivityTimeline items={[]} range="24h" loading={true} onRange={vi.fn()} retry={vi.fn()}/>);
    expect(screen.getByRole('status')).toHaveTextContent('Loading activity history');
    rerender(<ActivityTimeline items={[]} range="24h" loading={false} onRange={vi.fn()} retry={vi.fn()}/>);
    expect(screen.getByRole('status')).toHaveTextContent('No activity was recorded');
    rerender(<ActivityTimeline items={[]} range="24h" loading={false} error="History unavailable" onRange={vi.fn()} retry={vi.fn()}/>);
    expect(screen.getByRole('alert')).toHaveTextContent('History unavailable');

    const seen: EventRecord = { id: 8, ts: '2026-07-11T10:00:00Z', type: 'FALL', severity: 'critical', confidence: .9, evidence: {}, acknowledged: true };
    rerender(<AlertsLog events={[seen]} loading={false} onAcknowledge={vi.fn()} retry={vi.fn()}/>);
    expect(screen.getByText('Seen')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Mark as seen' })).not.toBeInTheDocument();
  });

  it('renders structured fallback feedback with its mandatory disclaimer', () => {
    render(<AIFeedbackPanel feedback={{ ts: '2026-07-11T10:00:00Z', mode: 'summary', headline: 'Recorded activity summary', detail: 'No activity data was available.', severity: 'info', recommendations: ['Check service health.'], disclaimer: 'This is not a medical diagnosis.', fallback: true }} loading={false} range="24h" onGenerate={vi.fn()}/>);
    expect(screen.getByText('Safe fallback')).toBeInTheDocument();
    expect(screen.getByText(/not a medical diagnosis/)).toBeInTheDocument();
  });
});
