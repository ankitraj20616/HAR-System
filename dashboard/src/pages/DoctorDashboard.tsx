import { TrendsPanel } from '../components/TrendsPanel';
import { AIFeedbackPanel } from '../components/AIFeedbackPanel';
import { AlertsLog } from '../components/AlertsLog';
import { useDashboardData } from '../hooks/useDashboardData';

export default function DoctorDashboard() {
  const data = useDashboardData();

  return (
    <div className="flex flex-col gap-10 pb-12">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
        <div className="w-full">
          <h2 className="text-xl font-bold tracking-tight text-slate-800 mb-4 px-2">Patient Activity Trends</h2>
          <TrendsPanel 
            trends={data.trends} 
            range={data.range} 
            loading={data.loading.trends} 
            error={data.errors.trends} 
            retry={() => data.loadRange(data.range)} 
          />
        </div>
        
        <div className="w-full">
          <h2 className="text-xl font-bold tracking-tight text-slate-800 mb-4 px-2">Clinical AI Assistant</h2>
          <AIFeedbackPanel 
            feedback={data.feedback} 
            loading={data.loading.feedback} 
            error={data.errors.feedback} 
            range={data.range} 
            onGenerate={data.generate} 
          />
        </div>
      </div>

      <div className="w-full">
        <h2 className="text-xl font-bold tracking-tight text-slate-800 mb-4 px-2">Historical Alerts Log</h2>
        <AlertsLog 
          events={data.events} 
          loading={data.loading.events} 
          error={data.errors.events} 
          pendingId={data.pendingAck} 
          onAcknowledge={data.acknowledge} 
          retry={() => data.loadRange(data.range)} 
        />
      </div>
    </div>
  );
}
