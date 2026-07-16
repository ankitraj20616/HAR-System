import type { EventRecord } from '../types';
import { formatTime, label, Panel, StateMessage } from './common';
import { motion, AnimatePresence } from 'framer-motion';

export function AlertsLog({ events, loading, error, pendingId, onAcknowledge, retry }: { events: EventRecord[]; loading: boolean; error?: string; pendingId?: number; onAcknowledge: (id: number) => void; retry: () => void }) {
  const sorted = [...events].sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime());
  
  return (
    <div className="flex flex-col gap-4">
      <div className="relative min-h-[300px] w-full bg-white border border-slate-200/50 rounded-[2.5rem] shadow-[0_20px_40px_-15px_rgba(0,0,0,0.05)] p-8 overflow-hidden">
        {loading && !events.length && (
          <div className="absolute inset-0 z-10 bg-white/80 backdrop-blur-sm flex items-center justify-center">
            <div className="flex flex-col items-center gap-3">
              <span className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm font-semibold text-slate-600">Loading alerts...</span>
            </div>
          </div>
        )}
        {error && !events.length ? (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-white">
            <div className="flex flex-col items-center gap-2 text-red-600">
              <span className="text-sm font-medium">{error}</span>
              <button onClick={retry} className="text-xs font-semibold underline hover:text-red-800 transition-colors">Try again</button>
            </div>
          </div>
        ) : !sorted.length && !loading ? (
          <div className="absolute inset-0 z-10 flex items-center justify-center text-slate-500 font-medium">
            No safety alerts were recorded in this period.
          </div>
        ) : (
          <div className="flex-1 max-h-[600px] overflow-y-auto custom-scrollbar pr-4 -mr-4">
            <ul className="flex flex-col gap-4">
              {sorted.map((event, i) => (
                <li 
                  key={event.id}
                  className={`p-5 rounded-2xl border flex flex-col md:flex-row md:items-start justify-between gap-4 transition-colors ${
                    !event.acknowledged 
                      ? event.severity === 'critical' ? 'bg-red-50/80 border-red-200' : 'bg-amber-50/80 border-amber-200'
                      : 'bg-white border-slate-100 opacity-70 hover:opacity-100'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                        !event.acknowledged 
                          ? event.severity === 'critical' ? 'bg-red-600 text-white' : 'bg-amber-500 text-white'
                          : 'bg-slate-200 text-slate-500'
                      }`}>
                        {event.acknowledged ? 'Seen' : 'New'}
                      </span>
                      <strong className={`font-bold tracking-tight text-lg ${!event.acknowledged ? (event.severity === 'critical' ? 'text-red-900' : 'text-amber-900') : 'text-slate-700'}`}>
                        {label(event.type)}
                      </strong>
                    </div>
                    <p className={`text-sm mb-3 ${!event.acknowledged ? (event.severity === 'critical' ? 'text-red-700' : 'text-amber-700') : 'text-slate-500'}`}>
                      {formatTime(event.ts)} · <span className="font-semibold">{Math.round(event.confidence * 100)}%</span> confidence
                    </p>
                    
                    <details className="group">
                      <summary className="text-xs font-semibold text-slate-500 cursor-pointer hover:text-slate-700 transition-colors inline-block mb-2">
                        Detection details
                      </summary>
                      <pre className="text-[10px] bg-slate-900 text-slate-300 p-3 rounded-xl overflow-x-auto border border-slate-800">
                        {JSON.stringify(event.evidence, null, 2)}
                      </pre>
                    </details>
                  </div>
                  
                  {!event.acknowledged && (
                    <button 
                      className={`flex-shrink-0 px-4 py-2 rounded-xl text-sm font-semibold transition-transform active:scale-[0.98] disabled:opacity-50 ${
                        event.severity === 'critical' 
                          ? 'bg-red-600 hover:bg-red-700 text-white shadow-sm' 
                          : 'bg-amber-500 hover:bg-amber-600 text-white shadow-sm'
                      }`}
                      disabled={pendingId === event.id} 
                      onClick={() => onAcknowledge(event.id)}
                    >
                      {pendingId === event.id ? 'Saving...' : 'Mark as seen'}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
