import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import AuthPage from './pages/AuthPage';
import DashboardLayout from './layouts/DashboardLayout';

export default function Router() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Marketing Route */}
        <Route path="/" element={<LandingPage />} />
        
        {/* Auth Route */}
        <Route path="/auth" element={<AuthPage />} />
        
        {/* Protected Application Routes */}
        <Route path="/dashboard" element={<DashboardLayout />} />
        
        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
