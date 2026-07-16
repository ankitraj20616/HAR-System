import type { EventRecord } from '../types';
import { formatTime, label } from './common';
import { WarningCircle } from '@phosphor-icons/react';
import { motion, AnimatePresence } from 'framer-motion';

export function FallAlertBanner({ event, acknowledging, onAcknowledge }: { event?: EventRecord; acknowledging: boolean; onAcknowledge: (id: number) => void }) {
  return (
    <AnimatePresence>
      {event && !event.acknowledged && (
        <motion.section 
          initial={{ opacity: 0, y: -20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          transition={{ type: 'spring', stiffness: 200, damping: 20 }}
          className="bg-red-600 text-white p-6 rounded-3xl shadow-xl flex flex-col md:flex-row gap-6 items-start md:items-center justify-between mb-8 overflow-hidden relative" 
          role="alert" 
          aria-labelledby="fall-heading"
        >
          {/* Pulsing background effect */}
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-red-500 to-transparent opacity-50 pointer-events-none" />
          
          <div className="flex gap-4 items-start relative z-10">
            <div className="bg-white text-red-600 p-3 rounded-2xl flex-shrink-0 animate-bounce">
              <WarningCircle weight="bold" className="w-8 h-8" />
            </div>
            <div className="flex flex-col">
              <p className="text-red-200 text-sm font-semibold uppercase tracking-wider mb-1">Immediate attention recommended</p>
              <h2 id="fall-heading" className="text-2xl font-bold tracking-tight mb-2">{label(event.type)} detected</h2>
              <p className="text-red-50 leading-relaxed max-w-[60ch]">
                Detected {formatTime(event.ts)} with {Math.round(event.confidence * 100)}% confidence. Check on the patient and follow your established response plan.
              </p>
              <p className="text-xs text-red-300 mt-3 font-medium">Acknowledging only marks this message as seen; it does not confirm the patient is safe.</p>
            </div>
          </div>
          <div className="flex gap-3 w-full md:w-auto relative z-10">
            <a className="px-6 py-3 bg-red-700 hover:bg-red-800 rounded-xl font-semibold transition-colors text-center w-full md:w-auto" href="#alerts">View details</a>
            <button 
              className="px-6 py-3 bg-white text-red-600 hover:bg-red-50 rounded-xl font-bold transition-transform active:scale-[0.98] w-full md:w-auto disabled:opacity-50" 
              disabled={acknowledging} 
              onClick={() => onAcknowledge(event.id)}
            >
              {acknowledging ? 'Saving...' : 'Mark as seen'}
            </button>
          </div>
        </motion.section>
      )}
    </AnimatePresence>
  );
}
