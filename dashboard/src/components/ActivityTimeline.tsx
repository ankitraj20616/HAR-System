import type { ActivityRecord, RangeKey } from '../types';
import { formatDuration, formatTime, label, Panel, StateMessage } from './common';
import { CaretDown } from '@phosphor-icons/react';
import { motion, AnimatePresence } from 'framer-motion';

const RANGE_OPTIONS: [RangeKey, string][] = [['1h', 'Last hour'], ['24h', '24 hours'], ['7d', '7 days'], ['30d', '30 days']];

export function RangeSelect({ value, onChange }: { value: RangeKey; onChange: (range: RangeKey) => void }) { 
  return (
    <div className="relative inline-block">
      <select 
        value={value} 
        onChange={e => onChange(e.target.value as RangeKey)}
        className="appearance-none bg-slate-50 border border-slate-200 text-slate-700 text-sm font-semibold rounded-xl pl-4 pr-10 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 cursor-pointer"
      >
        {RANGE_OPTIONS.map(([v, text]) => <option value={v} key={v}>{text}</option>)}
      </select>
      <CaretDown weight="bold" className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
    </div>
  ); 
}

export function calculateDurations(items: ActivityRecord[], end = Date.now()) {
  const sorted = [...items].sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime());
  return sorted.map((item, index) => ({ ...item, duration: item.duration_seconds ?? Math.max(0, ((index < sorted.length - 1 ? new Date(sorted[index + 1].ts).getTime() : Math.min(end, new Date(item.ts).getTime() + 300_000)) - new Date(item.ts).getTime()) / 1000) })).reverse();
}

export function ActivityTimeline({ items, range, loading, error, onRange, retry }: { items: ActivityRecord[]; range: RangeKey; loading: boolean; error?: string; onRange: (r: RangeKey) => void; retry: () => void }) {
  const rows = calculateDurations(items);
  
  return (
    <Panel title="" id="timeline" actions={<RangeSelect value={range} onChange={onRange} />}>
      <div className="h-full relative flex flex-col overflow-y-auto pr-2 custom-scrollbar">
        <AnimatePresence mode="wait">
          {loading ? (
            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0">
              <StateMessage kind="loading">Loading activity history…</StateMessage>
            </motion.div>
          ) : error ? (
            <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0">
              <StateMessage kind="error" retry={retry}>{error}</StateMessage>
            </motion.div>
          ) : !rows.length ? (
            <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0">
              <StateMessage kind="empty">No activity was recorded in this period.</StateMessage>
            </motion.div>
          ) : (
            <motion.ol 
              key="list" 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="relative border-l-2 border-slate-100 ml-4 space-y-6 pb-4"
            >
              {rows.map((row, i) => (
                <motion.li 
                  key={row.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: Math.min(i * 0.05, 0.5) }}
                  className="relative pl-6"
                >
                  <span 
                    className="absolute -left-[9px] top-1.5 w-4 h-4 rounded-full border-2 border-white"
                    style={{ backgroundColor: row.activity === 'LYING' ? '#10b981' : row.activity === 'WALKING' ? '#10b981' : row.activity === 'SITTING' ? '#3b82f6' : '#94a3b8' }}
                    aria-hidden="true"
                  />
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 bg-white border border-slate-100 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex flex-col">
                      <strong className="text-slate-900 font-bold capitalize tracking-tight">{label(row.activity)}</strong>
                      <span className="text-xs text-slate-500 font-medium mt-1">{formatTime(row.ts)}</span>
                    </div>
                    <span className="mt-2 sm:mt-0 px-3 py-1 bg-slate-50 text-slate-600 rounded-lg text-xs font-semibold whitespace-nowrap self-start sm:self-auto border border-slate-200">
                      {formatDuration(row.duration)}
                    </span>
                  </div>
                </motion.li>
              ))}
            </motion.ol>
          )}
        </AnimatePresence>
      </div>
    </Panel>
  );
}
