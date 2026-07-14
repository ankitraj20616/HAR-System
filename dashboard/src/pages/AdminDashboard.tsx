import { FormEvent, useEffect, useState } from 'react';
import { api } from '../api/client';
import { StatusBar } from '../components/StatusBar';
import { useDashboardData } from '../hooks/useDashboardData';
import { ShieldCheck, UserCircle, CheckCircle } from '@phosphor-icons/react';
import type { AppRole } from '../types';

export default function AdminDashboard() {
  const data = useDashboardData();
  const [users, setUsers] = useState<{user_id: string, email: string, role: AppRole, created_at: string}[]>([]);
  const [message, setMessage] = useState('');

  useEffect(() => {
    api.users().then(setUsers).catch(() => {});
  }, []);

  const submitRoleUpdate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); 
    const form = new FormData(event.currentTarget);
    try { 
      const result = await api.updateRole(String(form.get('user_id')), String(form.get('role')) as AppRole); 
      setMessage(`Role updated: ${result.user_id} → ${result.role}.`); 
      api.users().then(setUsers).catch(() => {});
    }
    catch (reason) { 
      setMessage(reason instanceof Error ? reason.message : 'Role update failed.'); 
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <StatusBar status={data.status} connection={data.connection} stale={data.stale} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="liquid-glass-light p-8 flex flex-col items-start">
          <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center mb-6 border border-indigo-100">
            <ShieldCheck weight="duotone" className="w-7 h-7" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight mb-2">Role Management</h2>
          <p className="text-slate-500 mb-8 max-w-[45ch]">
            Assign operational roles to users. Users must re-login to inherit new permissions.
          </p>

          <form onSubmit={submitRoleUpdate} className="w-full space-y-4">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-semibold text-slate-700">Target User</label>
              <select name="user_id" required defaultValue="" className="bg-white border border-slate-200 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                <option value="" disabled>Select a registered user...</option>
                {users.map(u => (
                  <option key={u.user_id} value={u.user_id}>
                    {u.email} — Current: {u.role.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm font-semibold text-slate-700">New Role</label>
              <select name="role" defaultValue="caregiver" className="bg-white border border-slate-200 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                <option value="pending">Pending (No Access)</option>
                <option value="caregiver">Caregiver (Live Feeds)</option>
                <option value="doctor">Doctor (Analytics)</option>
                <option value="admin">Admin (System Access)</option>
              </select>
            </div>

            <button className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 rounded-xl transition-colors active:scale-[0.98] mt-2">
              Apply Role Changes
            </button>
          </form>

          {message && (
            <div className="mt-4 w-full flex items-center gap-2 bg-emerald-50 text-emerald-700 p-4 rounded-xl border border-emerald-100 text-sm">
              <CheckCircle weight="fill" className="w-5 h-5" />
              <span>{message}</span>
            </div>
          )}
        </div>

        <div className="liquid-glass-light p-8">
          <div className="w-12 h-12 bg-slate-50 text-slate-600 rounded-xl flex items-center justify-center mb-6 border border-slate-200">
            <UserCircle weight="duotone" className="w-7 h-7" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight mb-2">Registered Users</h2>
          <p className="text-slate-500 mb-6">Directory of all accounts in the system.</p>

          <div className="overflow-y-auto max-h-[400px] border border-slate-100 rounded-2xl bg-slate-50/50">
            <ul className="divide-y divide-slate-100">
              {users.map(u => (
                <li key={u.user_id} className="p-4 flex items-center justify-between hover:bg-white transition-colors">
                  <div className="flex flex-col">
                    <span className="font-medium text-slate-900">{u.email}</span>
                    <span className="text-xs text-slate-400 font-mono mt-1">{u.user_id}</span>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider ${
                    u.role === 'admin' ? 'bg-indigo-100 text-indigo-700' :
                    u.role === 'doctor' ? 'bg-blue-100 text-blue-700' :
                    u.role === 'caregiver' ? 'bg-emerald-100 text-emerald-700' :
                    'bg-slate-200 text-slate-600'
                  }`}>
                    {u.role}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
