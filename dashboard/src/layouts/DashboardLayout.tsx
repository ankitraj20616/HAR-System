import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { clearSession, getAccessToken } from '../auth/session';
import type { AuthenticatedUser } from '../types';
import { Heartbeat, SignOut } from '@phosphor-icons/react';

// Role-specific imports
import CaregiverDashboard from '../pages/CaregiverDashboard';
import DoctorDashboard from '../pages/DoctorDashboard';
import AdminDashboard from '../pages/AdminDashboard';
import PendingDashboard from '../pages/PendingDashboard';

export default function DashboardLayout() {
  const [identity, setIdentity] = useState<AuthenticatedUser | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      navigate('/auth');
      return;
    }

    api.me()
      .then(user => setIdentity(user))
      .catch(() => {
        clearSession();
        navigate('/auth');
      })
      .finally(() => setLoading(false));
  }, [navigate]);

  const handleSignOut = () => {
    clearSession();
    navigate('/');
  };

  if (loading) {
    return <div className="min-h-[100dvh] bg-zinc-50 flex items-center justify-center text-zinc-500 font-medium">Loading workspace...</div>;
  }

  if (!identity) return null;

  // Render role-specific content
  let Content;
  switch (identity.role) {
    case 'caregiver':
      Content = <CaregiverDashboard />;
      break;
    case 'doctor':
      Content = <DoctorDashboard />;
      break;
    case 'admin':
      Content = <AdminDashboard />;
      break;
    case 'pending':
    default:
      Content = <PendingDashboard />;
      break;
  }

  return (
    <div className="min-h-[100dvh] bg-zinc-50 text-zinc-950 font-sans selection:bg-brand-500/20">
      {/* Top Navbar */}
      <header className="sticky top-0 z-40 bg-white/70 backdrop-blur-xl border-b border-zinc-200/50">
        <div className="max-w-[1400px] mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Heartbeat weight="fill" className="text-brand-600 w-6 h-6" />
            <span className="font-bold tracking-tight">HAR<span className="text-zinc-400">.sys</span></span>
            <div className="h-4 w-[1px] bg-zinc-300 mx-2" />
            <span className="text-sm font-medium text-zinc-600 capitalize">{identity.role} Portal</span>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-sm text-zinc-500 hidden sm:inline-block">
              {identity.email || identity.user_id}
            </span>
            <button 
              onClick={handleSignOut}
              className="p-2 text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 rounded-full transition-colors"
              title="Sign Out"
            >
              <SignOut weight="bold" className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-[1400px] mx-auto px-4 sm:px-6 py-8">
        {Content}
      </main>
    </div>
  );
}
