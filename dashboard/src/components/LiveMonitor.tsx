import type { SystemStatus } from '../types';
import { formatTime, label, Panel, StateMessage } from './common';
import { motion, AnimatePresence } from 'framer-motion';

export function LiveMonitor({ status, loading, error, stale, retry }: { status: SystemStatus | null; loading: boolean; error?: string; stale: boolean; retry: () => void }) {
  return (
    <Panel title="" id="live">
      <div className="h-full min-h-[300px] relative flex flex-col">
        <AnimatePresence mode="wait">
          {loading && !status ? (
            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0">
              <StateMessage kind="loading">Loading live stream...</StateMessage>
            </motion.div>
          ) : error && !status ? (
            <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0">
              <StateMessage kind="error" retry={retry}>{error}</StateMessage>
            </motion.div>
          ) : status ? (
            <motion.div key="content" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="flex-1 flex flex-col items-center justify-center p-8 bg-zinc-950 rounded-3xl overflow-hidden relative border border-zinc-800">
              {/* Fake video background effect */}
              <div className="absolute inset-0 opacity-20 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-zinc-700 to-transparent mix-blend-screen pointer-events-none" />
              
              <motion.div 
                key={status.activity}
                initial={{ scale: 0.8, opacity: 0 }} 
                animate={{ scale: 1, opacity: 1 }} 
                className="relative z-10 w-32 h-32 rounded-full border-2 flex items-center justify-center mb-6 shadow-2xl backdrop-blur-md bg-white/5"
                style={{ 
                  borderColor: status.activity === 'LYING' ? '#ef4444' : status.activity === 'SITTING' ? '#3b82f6' : status.activity === 'WALKING' ? '#10b981' : '#64748b' 
                }}
              >
                <span className="text-5xl text-white font-bold tracking-tighter">
                  {status.activity === 'UNKNOWN' ? '?' : status.activity[0]}
                </span>
                
                {/* Ping animation wrapper */}
                <div className="absolute inset-0 rounded-full animate-ping opacity-20" style={{ backgroundColor: status.activity === 'LYING' ? '#ef4444' : status.activity === 'WALKING' ? '#10b981' : 'transparent' }} />
              </motion.div>

              <div className="text-center relative z-10">
                <h3 className="text-3xl font-bold tracking-tight text-white capitalize mb-2">{label(status.activity)}</h3>
                <div className="flex items-center justify-center gap-4">
                  <p className="px-3 py-1 bg-white/10 rounded-full text-sm font-semibold text-zinc-300">
                    Confidence: <span className="text-white">{Math.round(status.confidence * 100)}%</span>
                  </p>
                </div>
                <p className={`mt-6 text-xs ${stale ? 'text-amber-500 font-semibold' : 'text-zinc-500'}`}>
                  {stale ? 'Warning: Stream disconnected. ' : 'Live update: '}
                  {formatTime(status.last_update)}
                </p>
              </div>
            </motion.div>
          ) : (
            <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0">
              <StateMessage kind="empty">Waiting for camera feed initialization.</StateMessage>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Panel>
  );
}
