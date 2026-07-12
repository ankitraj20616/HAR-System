import { FormEvent, useEffect, useMemo, useState } from 'react';
import { createClient, type Session, type SupabaseClient } from '@supabase/supabase-js';
import App from '../App';
import { api, ApiError } from '../api/client';
import type { AppRole, AuthenticatedUser } from '../types';
import { setSessionBridge } from './session';

type Mode = 'login' | 'signup';
type PublicConfig = { supabase_url: string; supabase_publishable_key: string };

export default function AuthGate() {
  const [client, setClient] = useState<SupabaseClient>();
  const [session, setSession] = useState<Session | null>();
  const [identity, setIdentity] = useState<AuthenticatedUser>();
  const [mode, setMode] = useState<Mode>('login');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    let active = true; let unsubscribe: (() => void) | undefined;
    fetch('/api/auth/config').then(async response => {
      if (!response.ok) throw new Error('Authentication configuration is unavailable.');
      const config = await response.json() as PublicConfig;
      const supabase = createClient(config.supabase_url, config.supabase_publishable_key);
      if (!active) return;
      setClient(supabase);
      const { data } = await supabase.auth.getSession();
      if (active) setSession(data.session);
      const { data: listener } = supabase.auth.onAuthStateChange((_event, next) => {
        setSession(next); setIdentity(undefined); setError('');
      });
      unsubscribe = () => listener.subscription.unsubscribe();
    }).catch(reason => { if (active) { setError(reason instanceof Error ? reason.message : 'Authentication unavailable.'); setBusy(false); } });
    return () => { active = false; unsubscribe?.(); };
  }, []);

  useEffect(() => {
    if (!client || session === undefined) return;
    const refresh = async () => {
      const { data, error: refreshError } = await client.auth.refreshSession();
      if (refreshError) return undefined;
      setSessionBridge(data.session?.access_token, refresh);
      return data.session?.access_token;
    };
    setSessionBridge(session?.access_token, refresh);
    if (!session) { setIdentity(undefined); setBusy(false); return; }
    setBusy(true);
    api.me().then(setIdentity).catch(reason => {
      setError(reason instanceof ApiError ? reason.message : 'Could not verify this session.');
    }).finally(() => setBusy(false));
    return () => setSessionBridge(undefined);
  }, [client, session]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!client) return;
    const form = new FormData(event.currentTarget);
    const email = String(form.get('email') || ''); const password = String(form.get('password') || '');
    setBusy(true); setError(''); setNotice('');
    const result = mode === 'login'
      ? await client.auth.signInWithPassword({ email, password })
      : await client.auth.signUp({ email, password });
    if (result.error) setError(result.error.message);
    else if (mode === 'signup' && !result.data.session) setNotice('Account created. Please verify your email, then sign in.');
    setBusy(false);
  };

  const adminPanel = useMemo(() => identity?.role === 'admin' ? <RoleAdmin/> : null, [identity?.role]);

  if (busy && !identity) return <main className="auth-shell"><section className="auth-card" role="status">Checking your secure session…</section></main>;
  if (!session || !identity) return <main className="auth-shell"><section className="auth-card">
    <p className="brand-mark">HAR</p><h1>{mode === 'login' ? 'Sign in' : 'Create account'}</h1>
    <p>Use your approved account to open the patient monitoring dashboard.</p>
    {error && <p role="alert" className="error-text">{error}</p>}{notice && <p role="status" className="notice-text">{notice}</p>}
    <form onSubmit={submit}><label>Email<input name="email" type="email" autoComplete="email" required/></label><label>Password<input name="password" type="password" minLength={8} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required/></label><button disabled={!client || busy}>{busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Sign up'}</button></form>
    <button className="text-button" onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(''); setNotice(''); }}>{mode === 'login' ? 'Need an account? Sign up' : 'Already registered? Sign in'}</button>
  </section></main>;
  if (identity.role === 'pending') return <main className="auth-shell"><section className="auth-card"><h1>Approval pending</h1><p>Your email is verified, but an administrator must assign your caregiver, doctor, or admin role before monitoring data is available.</p><button onClick={() => client?.auth.signOut()}>Sign out</button></section></main>;
  return <><div className="user-bar"><span>Signed in as {identity.email || identity.user_id} · {identity.role}</span><button onClick={() => client?.auth.signOut()}>Sign out</button></div>{adminPanel}<App/></>;
}

function RoleAdmin() {
  const [message, setMessage] = useState('');
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    try { const result = await api.updateRole(String(form.get('user_id')), String(form.get('role')) as AppRole); setMessage(`Role updated: ${result.user_id} → ${result.role}. User must refresh the session.`); }
    catch (reason) { setMessage(reason instanceof Error ? reason.message : 'Role update failed.'); }
  };
  return <details className="admin-panel"><summary>Admin: assign a user role</summary><form onSubmit={submit}><label>User UUID<input name="user_id" required pattern="[0-9a-fA-F-]{36}"/></label><label>Role<select name="role" defaultValue="caregiver"><option value="pending">Pending</option><option value="caregiver">Caregiver</option><option value="doctor">Doctor</option><option value="admin">Admin</option></select></label><button>Save role</button></form>{message && <p role="status">{message}</p>}</details>;
}
