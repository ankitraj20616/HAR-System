import { FormEvent, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { getAccessToken, setSessionBridge, clearSession } from '../auth/session';
import { motion } from 'framer-motion';
import { Heartbeat, WarningCircle } from '@phosphor-icons/react';
import type { AuthenticatedUser } from '../types';

type Mode = 'login' | 'signup';

export default function AuthPage() {
  const [mode, setMode] = useState<Mode>('login');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const token = getAccessToken();
    if (!token) { setBusy(false); return; }
    api.me().then(() => navigate('/dashboard'))
      .catch(() => clearSession())
      .finally(() => setBusy(false));
  }, [navigate]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get('email') || '');
    const password = String(form.get('password') || '');
    setBusy(true); setError(''); setNotice('');

    try {
      if (mode === 'signup') {
        const response = await fetch('/api/auth/signup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        });
        const data = await response.json();
        if (!response.ok) { setError(data.detail || 'Signup failed'); setBusy(false); return; }
        setNotice('Account created! Please sign in.');
        setMode('login');
      } else {
        const response = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        });
        const data = await response.json();
        if (!response.ok) { setError(data.detail || 'Login failed'); setBusy(false); return; }
        setSessionBridge(data.access_token);
        navigate('/dashboard');
      }
    } catch {
      setError('Unable to reach the server.');
    }
    setBusy(false);
  };

  if (busy) return <div className="min-h-[100dvh] bg-zinc-950 flex items-center justify-center text-zinc-500">Checking session...</div>;

  return (
    <div className="min-h-[100dvh] bg-zinc-950 text-zinc-50 flex">
      {/* Left side: Form */}
      <div className="w-full lg:w-1/2 flex flex-col justify-center px-8 md:px-16 xl:px-24 z-10">
        <div className="max-w-md w-full mx-auto">
          <div className="flex items-center gap-2 mb-12 cursor-pointer" onClick={() => navigate('/')}>
            <Heartbeat weight="fill" className="text-brand-500 w-8 h-8" />
            <span className="text-xl font-bold tracking-tight">HAR<span className="text-zinc-500">.sys</span></span>
          </div>

          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ type: 'spring' }}>
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight mb-2">
              {mode === 'login' ? 'Welcome back' : 'Create an account'}
            </h1>
            <p className="text-zinc-400 mb-8">
              {mode === 'login' 
                ? 'Enter your credentials to access the dashboard.' 
                : 'Register to request access to the monitoring system.'}
            </p>

            {error && (
              <div className="flex items-center gap-2 bg-red-950/30 text-red-400 border border-red-900/50 p-4 rounded-xl mb-6 text-sm">
                <WarningCircle className="w-5 h-5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
            
            {notice && (
              <div className="flex items-center gap-2 bg-brand-950/30 text-brand-400 border border-brand-900/50 p-4 rounded-xl mb-6 text-sm">
                <span>{notice}</span>
              </div>
            )}

            <form onSubmit={submit} className="space-y-5">
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-zinc-300">Email Address</label>
                <input 
                  name="email" 
                  type="email" 
                  required 
                  className="bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors"
                  placeholder="name@example.com"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-zinc-300">Password</label>
                <input 
                  name="password" 
                  type="password" 
                  required 
                  minLength={8}
                  className="bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors"
                  placeholder="••••••••"
                />
              </div>

              <button 
                disabled={busy}
                className="w-full bg-zinc-100 text-zinc-950 font-semibold rounded-xl py-3 mt-4 hover:bg-white transition-all active:scale-[0.98] disabled:opacity-50"
              >
                {busy ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Sign Up'}
              </button>
            </form>

            <p className="mt-8 text-center text-zinc-500 text-sm">
              {mode === 'login' ? "Don't have an account? " : "Already registered? "}
              <button 
                onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(''); setNotice(''); }}
                className="text-zinc-300 hover:text-white underline decoration-zinc-700 underline-offset-4"
              >
                {mode === 'login' ? 'Sign up here' : 'Sign in here'}
              </button>
            </p>
          </motion.div>
        </div>
      </div>

      {/* Right side: Abstract Art */}
      <div className="hidden lg:flex w-1/2 bg-zinc-900 relative overflow-hidden items-center justify-center">
        <div className="absolute inset-0 bg-brand-900/10 mix-blend-screen" />
        <div className="absolute top-[-10%] right-[-10%] w-[70%] h-[70%] bg-brand-600/20 blur-[120px] rounded-full" />
        
        <div className="relative z-10 max-w-md liquid-glass p-8 rounded-[2rem] border border-white/5">
          <Heartbeat weight="duotone" className="w-16 h-16 text-brand-400 mb-6" />
          <h2 className="text-2xl font-bold tracking-tight mb-2">High-Agency Reliability</h2>
          <p className="text-zinc-400 leading-relaxed">
            Ensuring patient safety with edge-computed fall detection and continuous posture monitoring, delivered securely.
          </p>
        </div>
      </div>
    </div>
  );
}
