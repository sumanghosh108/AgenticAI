import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { Layout } from '@/components/layout/Layout';
import { LandingPage } from '@/pages/Landing/LandingPage';
import { LoginPage } from '@/pages/Auth/LoginPage';
import { SignupPage } from '@/pages/Auth/SignupPage';
import { DashboardPage } from '@/pages/Dashboard/DashboardPage';
import { AnalysisPage } from '@/pages/Analysis/AnalysisPage';
import { ReportPage } from '@/pages/Report/ReportPage';
import { MetricsPage } from '@/pages/Metrics/MetricsPage';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  if (!isAuthenticated) return <Navigate to={`/login${location.search}`} replace />;
  return <>{children}</>;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/" element={<PublicRoute><LandingPage /></PublicRoute>} />
      <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
      <Route path="/signup" element={<PublicRoute><SignupPage /></PublicRoute>} />

      {/* Protected routes inside Layout */}
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/analysis" element={<AnalysisPage />} />
        <Route path="/reports" element={<ReportPage />} />
        <Route path="/metrics" element={<MetricsPage />} />
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
