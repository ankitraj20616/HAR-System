import { Hourglass, LockKey } from '@phosphor-icons/react';
import { motion } from 'framer-motion';

export default function PendingDashboard() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: 'spring', stiffness: 100, damping: 20 }}
        className="bg-white p-10 rounded-[2.5rem] border border-slate-200/50 shadow-[0_20px_40px_-15px_rgba(0,0,0,0.05)] max-w-md w-full"
      >
        <div className="w-16 h-16 bg-amber-50 text-amber-500 rounded-2xl flex items-center justify-center mx-auto mb-6">
          <Hourglass weight="duotone" className="w-8 h-8 animate-pulse" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight mb-2">Approval Pending</h1>
        <p className="text-slate-500 mb-8 leading-relaxed">
          Your account has been created successfully, but you need an administrator to assign your role before you can access the monitoring systems.
        </p>

        <div className="flex items-center justify-center gap-2 text-sm text-slate-400 bg-slate-50 py-3 rounded-xl">
          <LockKey weight="bold" />
          <span>Restricted Access Area</span>
        </div>
      </motion.div>
    </div>
  );
}
