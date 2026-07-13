import type { Feedback, RangeKey } from '../types';
import { formatTime, label, Panel, StateMessage } from './common';
import { Sparkle, ShieldWarning } from '@phosphor-icons/react';
import { motion, AnimatePresence } from 'framer-motion';

export function AIFeedbackPanel({ feedback, loading, error, range, onGenerate }: { feedback: Feedback | null; loading: boolean; error?: string; range: RangeKey; onGenerate: (mode: 'feedback' | 'summary') => void }) {
  return (
    <div className="flex flex-col gap-4 h-full">
      <div className="flex items-center justify-end">
        <div className="flex gap-2">
          <button 
            className="px-4 py-2 bg-indigo-50 text-indigo-600 font-semibold rounded-xl text-sm hover:bg-indigo-100 transition-colors disabled:opacity-50" 
            disabled={loading} 
            onClick={() => onGenerate('feedback')}
          >
            Refresh advice
          </button>
          <button 
            className="px-4 py-2 bg-white text-slate-600 border border-slate-200 font-semibold rounded-xl text-sm hover:bg-slate-50 hover:text-slate-900 transition-colors disabled:opacity-50 shadow-sm" 
            disabled={loading} 
            onClick={() => onGenerate('summary')}
          >
            Period summary
          </button>
        </div>
      </div>
      <div className="relative min-h-[350px] flex-1 w-full bg-white border border-slate-200/50 rounded-[2.5rem] shadow-[0_20px_40px_-15px_rgba(0,0,0,0.05)] p-8 overflow-hidden">
        {loading && !feedback && (
          <div className="absolute inset-0 z-10 bg-white/80 backdrop-blur-sm flex items-center justify-center">
            <div className="flex flex-col items-center gap-3">
              <span className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm font-semibold text-slate-600">Analyzing data with AI...</span>
            </div>
          </div>
        )}
        {error && !feedback ? (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-white">
            <div className="flex flex-col items-center gap-2 text-red-600">
              <span className="text-sm font-medium">{error}</span>
            </div>
          </div>
        ) : !feedback && !loading ? (
          <div className="absolute inset-0 z-10 flex items-center justify-center text-slate-500 font-medium text-center p-8">
            No feedback is available yet. Request advice for the {range} period.
          </div>
        ) : feedback ? (
          <article 
            key={feedback.ts}
            className={`h-full flex flex-col p-6 rounded-3xl border ${
              feedback.severity === 'critical' ? 'bg-red-50/50 border-red-100' : 
              feedback.severity === 'warning' ? 'bg-amber-50/50 border-amber-100' : 
              'bg-indigo-50/30 border-indigo-100/50'
            }`}
          >
            <div className="flex items-center gap-3 mb-6 flex-wrap">
              <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                feedback.severity === 'critical' ? 'bg-red-100 text-red-700' : 
                feedback.severity === 'warning' ? 'bg-amber-100 text-amber-700' : 
                'bg-indigo-100 text-indigo-700'
              }`}>
                {label(feedback.severity)}
              </span>
              <span className="text-sm font-medium text-slate-500">
                {label(feedback.mode)} · {formatTime(feedback.ts)}
              </span>
              {feedback.fallback && <span className="px-2 py-0.5 bg-slate-200 text-slate-600 rounded text-xs font-semibold">Safe fallback</span>}
            </div>

            <div className="flex items-start gap-4 mb-4">
              <div className={`p-2 rounded-xl flex-shrink-0 mt-1 ${
                feedback.severity === 'critical' ? 'bg-red-100 text-red-600' : 
                feedback.severity === 'warning' ? 'bg-amber-100 text-amber-600' : 
                'bg-indigo-100 text-indigo-600'
              }`}>
                <Sparkle weight="fill" className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-xl font-bold tracking-tight text-slate-900 mb-2">{feedback.headline}</h3>
                <p className="text-slate-600 leading-relaxed text-sm md:text-base">{feedback.detail}</p>
              </div>
            </div>

            {feedback.recommendations?.length > 0 && (
              <div className="mt-4 pl-14">
                <h4 className="text-sm font-bold text-slate-900 mb-2">Suggested next steps:</h4>
                <ul className="space-y-2">
                  {feedback.recommendations.map((item, i) => (
                    <li key={`${item}-${i}`} className="flex items-start gap-2 text-sm text-slate-600">
                      <span className="text-indigo-400 mt-0.5">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <footer className="mt-auto pt-6 border-t border-slate-200/50 flex items-start gap-2 text-xs text-slate-500">
              <ShieldWarning weight="fill" className="w-4 h-4 flex-shrink-0 text-slate-400" />
              <p><strong>Safety note:</strong> {feedback.disclaimer || 'This automated information is assistive only and is not a medical diagnosis.'}</p>
            </footer>

            {error && (
              <div className="mt-4 p-3 bg-red-50 text-red-600 rounded-xl text-sm border border-red-100 font-medium">
                Could not refresh: {error}
              </div>
            )}
          </article>
        ) : null}
      </div>
    </div>
  );
}
