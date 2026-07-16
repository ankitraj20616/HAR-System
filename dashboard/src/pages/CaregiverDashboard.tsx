import { FallAlertBanner } from '../components/FallAlertBanner';
import { LiveMonitor } from '../components/LiveMonitor';
import { ActivityTimeline } from '../components/ActivityTimeline';
import { StatusBar } from '../components/StatusBar';
import { useDashboardData } from '../hooks/useDashboardData';

export default function CaregiverDashboard() {
  const data = useDashboardData();

  return (
    <div className="flex flex-col gap-8 pb-12">
      <div className="w-full">
        <StatusBar status={data.status} connection={data.connection} stale={data.stale} />
      </div>
      
      <div className="w-full">
        <FallAlertBanner 
          event={data.criticalEvent} 
          acknowledging={data.pendingAck === data.criticalEvent?.id} 
          onAcknowledge={data.acknowledge}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Live Monitor Card */}
        <div className="flex flex-col gap-4">
          <div className="bg-white rounded-[2.5rem] p-8 md:p-10 border border-slate-200/50 shadow-[0_20px_40px_-15px_rgba(0,0,0,0.05)] min-h-[450px] flex flex-col relative overflow-hidden group">
            <LiveMonitor 
              status={data.status} 
              loading={data.loading.status} 
              error={data.errors.status} 
              stale={data.stale} 
              retry={() => data.loadStatus()} 
            />
          </div>
          <div className="px-6 flex flex-col gap-1">
            <h2 className="text-xl font-bold tracking-tight text-slate-900">Live Monitoring Feed</h2>
            <p className="text-sm text-slate-500 font-medium">Real-time edge AI posture tracking & fall detection</p>
          </div>
        </div>
        
        {/* Recent Activity Card */}
        <div className="flex flex-col gap-4">
          <div className="bg-white rounded-[2.5rem] p-8 md:p-10 border border-slate-200/50 shadow-[0_20px_40px_-15px_rgba(0,0,0,0.05)] h-[450px] flex flex-col relative overflow-hidden">
            <div className="flex-1 overflow-y-auto pr-2 -mr-2">
              <ActivityTimeline 
                items={data.timeline} 
                range={data.range} 
                loading={data.loading.timeline} 
                error={data.errors.timeline} 
                onRange={data.setRange} 
                retry={() => data.loadRange(data.range)} 
              />
            </div>
          </div>
          <div className="px-6 flex flex-col gap-1">
            <h2 className="text-xl font-bold tracking-tight text-slate-900">Activity History</h2>
            <p className="text-sm text-slate-500 font-medium">Chronological record of patient movements</p>
          </div>
        </div>
      </div>
    </div>
  );
}
