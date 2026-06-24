import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/AppLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import ArchitecturePage from "@/pages/Architecture";
import DashboardPage from "@/pages/Dashboard";
import LoginPage from "@/pages/Login";
import NotFoundPage from "@/pages/NotFound";
import SignupPage from "@/pages/Signup";
import UrlAnalyticsPage from "@/pages/UrlAnalytics";

function RootRedirect() {
  const { user, loading } = useAuth();
  if (loading) return null;
  return <Navigate to={user ? "/dashboard" : "/login"} replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <AppLayout>
                <DashboardPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard/urls/:id"
          element={
            <ProtectedRoute>
              <AppLayout>
                <UrlAnalyticsPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/architecture"
          element={
            <ProtectedRoute>
              <AppLayout>
                <ArchitecturePage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AuthProvider>
  );
}
