import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { RangeKey, TrendsResponse } from '../types';
import { formatDuration, label, Panel, StateMessage } from './common';
import { motion } from 'framer-motion';

export function TrendsPanel({ trends, loading, error, range, retry }: { trends: TrendsResponse | null; loading: boolean; error?: string; range: RangeKey; retry: () => void }) {
  const rows = (trends?.activities || []).filter(item => item.duration_seconds > 0);
  
  return (
    <div className="flex flex-col gap-4">
      <div className="relative min-h-[300px] w-full bg-white border border-slate-200/50 rounded-[2.5rem] shadow-[0_20px_40px_-15px_rgba(0,0,0,0.05)] p-8 overflow-hidden">
        {loading && !trends && (
          <div className="absolute inset-0 z-10 bg-white/80 backdrop-blur-sm flex items-center justify-center">
            <div className="flex flex-col items-center gap-3">
              <span className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm font-semibold text-slate-600">Calculating trends...</span>
            </div>
          </div>
        )}
        {error && !trends ? (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-white">
            <div className="flex flex-col items-center gap-2 text-red-600">
              <span className="text-sm font-medium">{error}</span>
              <button onClick={retry} className="text-xs font-semibold underline hover:text-red-800 transition-colors">Try again</button>
            </div>
          </div>
        ) : !rows.length && !loading ? (
          <div className="absolute inset-0 z-10 flex items-center justify-center text-slate-500 font-medium">
            Not enough activity data to show trends for this period.
          </div>
        ) : (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="w-full h-full min-h-[250px]"
            role="img" 
            aria-label={`Bar chart of time spent per activity over ${range}`}
          >
            <ResponsiveContainer width="100%" height={270}>
              <BarChart data={rows} margin={{ left: 0, right: 0, top: 0, bottom: 25 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis 
                  dataKey="activity" 
                  tickFormatter={label} 
                  angle={-20} 
                  textAnchor="end" 
                  height={55} 
                  stroke="#94a3b8" 
                  tick={{ fontSize: 12, fontWeight: 500 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis 
                  tickFormatter={v => `${Math.round(Number(v) / 60)}m`} 
                  width={45} 
                  stroke="#94a3b8" 
                  tick={{ fontSize: 12, fontWeight: 500 }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip 
                  formatter={(value) => [formatDuration(Number(value)), 'Time']} 
                  labelFormatter={value => label(String(value ?? ''))}
                  contentStyle={{ borderRadius: '16px', border: '1px solid #f1f5f9', boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)', fontWeight: 500, fontSize: '14px', padding: '12px' }}
                />
                <Bar 
                  dataKey="duration_seconds" 
                  name="Duration" 
                  fill="#6366f1" 
                  radius={[8, 8, 8, 8]} 
                  animationDuration={1500}
                />
              </BarChart>
            </ResponsiveContainer>
            
            <table className="sr-only">
              <caption>Text alternative: activity duration</caption>
              <thead>
                <tr><th>Activity</th><th>Duration</th><th>Updates</th></tr>
              </thead>
              <tbody>
                {rows.map(row => (
                  <tr key={row.activity}>
                    <td>{label(row.activity)}</td>
                    <td>{formatDuration(row.duration_seconds)}</td>
                    <td>{row.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </motion.div>
        )}
      </div>
    </div>
  );
}
