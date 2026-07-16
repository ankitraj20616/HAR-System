import { FormEvent, useEffect, useMemo, useState } from 'react';
import App from '../App';
import { api, ApiError } from '../api/client';
import type { AppRole, AuthenticatedUser } from '../types';
import { setSessionBridge, getAccessToken, clearSession } from './session';

type Mode = 'login' | 'signup';

interface LoginResult { access_token: string; expires_in: number; user: AuthenticatedUser }

export default function AuthGate() {
  const [identity, setIdentity] = useState<AuthenticatedUser>();
  const [mode, setMode] = useState<Mode>('login');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(true);

  // On mount, check if we have a saved token
  useEffect(() => {
    const token = getAccessToken();
    if (!token) { setBusy(false); return; }
    // Verify the saved token
    api.me().then(user => {
      setIdentity(user);
    }).catch(() => {
      clearSession();
    }).finally(() => setBusy(false));
  }, []);

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
        const data: LoginResult = await response.json();
        if (!response.ok) { setError((data as any).detail || 'Login failed'); setBusy(false); return; }
        setSessionBridge(data.access_token);
        setIdentity(data.user);
      }
    } catch {
      setError('Unable to reach the server.');
    }
    setBusy(false);
  };

  const signOut = () => {
    clearSession();
    setIdentity(undefined);
    setError(''); setNotice('');
  };

  const adminPanel = useMemo(() => identity?.role === 'admin' ? <RoleAdmin/> : null, [identity?.role]);

  if (busy && !identity) return <main className="auth-shell"><section className="auth-card" role="status">Checking your session…</section></main>;
  if (!identity) return <main className="auth-shell"><section className="auth-card">
    <p className="brand-mark">HAR</p><h1>{mode === 'login' ? 'Sign in' : 'Create account'}</h1>
    <p>Use your approved account to open the patient monitoring dashboard.</p>
    {error && <p role="alert" className="error-text">{error}</p>}{notice && <p role="status" className="notice-text">{notice}</p>}
    <form onSubmit={submit}><label>Email<input name="email" type="email" autoComplete="email" required/></label><label>Password<input name="password" type="password" minLength={8} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required/></label><button disabled={busy}>{busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Sign up'}</button></form>
    <button className="text-button" onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(''); setNotice(''); }}>{mode === 'login' ? 'Need an account? Sign up' : 'Already registered? Sign in'}</button>
  </section></main>;
  if (identity.role === 'pending') return <main className="auth-shell"><section className="auth-card"><h1>Approval pending</h1><p>Your email is verified, but an administrator must assign your caregiver, doctor, or admin role before monitoring data is available.</p><button onClick={signOut}>Sign out</button></section></main>;
  return <><div className="user-bar"><span>Signed in as {identity.email || identity.user_id} · {identity.role}</span><button onClick={signOut}>Sign out</button></div>{adminPanel}<App/></>;
}

function RoleAdmin() {
  const [message, setMessage] = useState('');
  const [users, setUsers] = useState<{user_id: string, email: string, role: AppRole, created_at: string}[]>([]);

  useEffect(() => {
    api.users().then(setUsers).catch(() => {});
  }, []);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    try { 
      const result = await api.updateRole(String(form.get('user_id')), String(form.get('role')) as AppRole); 
      setMessage(`Role updated: ${result.user_id} → ${result.role}.`); 
      api.users().then(setUsers); // Refresh the list
    }
    catch (reason) { setMessage(reason instanceof Error ? reason.message : 'Role update failed.'); }
  };
  return <details className="admin-panel"><summary>Admin: assign a user role</summary>
    <form onSubmit={submit}>
      <label>User
        <select name="user_id" required defaultValue="">
          <option value="" disabled>Select a user</option>
          {users.map(u => (
            <option key={u.user_id} value={u.user_id}>
              {u.email} ({u.role})
            </option>
          ))}
        </select>
      </label>
      <label>Role
        <select name="role" defaultValue="caregiver">
          <option value="pending">Pending</option>
          <option value="caregiver">Caregiver</option>
          <option value="doctor">Doctor</option>
          <option value="admin">Admin</option>
        </select>
      </label>
      <button>Save role</button>
    </form>
    {message && <p role="status">{message}</p>}
  </details>;
}
