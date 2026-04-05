import { useAuth0 } from "@auth0/auth0-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { configureApiClient, resetApiClient } from "./api/http";
import { readUserRoles } from "./auth/config";
import { AppShell } from "./components/AppShell";
import { FullScreenStatus } from "./components/FullScreenStatus";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AdminPage } from "./pages/AdminPage";
import { ForbiddenPage } from "./pages/ForbiddenPage";
import { MonitoringPage } from "./pages/MonitoringPage";
import "./App.css";

export default function App() {
  const { getAccessTokenSilently, loginWithRedirect, logout, user } = useAuth0();
  const navigate = useNavigate();
  const [clientReady, setClientReady] = useState(false);

  const roles = useMemo(() => readUserRoles(user as Record<string, unknown> | undefined), [user]);
  const isAdmin = roles.includes("Admin");
  const userName = user?.name ?? user?.email ?? user?.nickname ?? "Користувач";

  const handleUnauthorized = useCallback(() => {
    void loginWithRedirect({
      appState: {
        returnTo: `${window.location.pathname}${window.location.search}${window.location.hash}`,
      },
    });
  }, [loginWithRedirect]);

  const handleForbidden = useCallback(() => {
    navigate("/forbidden", { replace: true });
  }, [navigate]);

  useEffect(() => {
    configureApiClient({
      getAccessToken: getAccessTokenSilently,
      onUnauthorized: handleUnauthorized,
      onForbidden: handleForbidden,
    });
    setClientReady(true);

    return () => {
      resetApiClient();
    };
  }, [getAccessTokenSilently, handleForbidden, handleUnauthorized]);

  if (!clientReady) {
    return (
      <FullScreenStatus
        title="Готуємо захищене з'єднання"
        description="Налаштовуємо авторизований доступ до API та realtime-оновлень."
        loading
      />
    );
  }

  return (
    <Routes>
      <Route path="/forbidden" element={<ForbiddenPage />} />
      <Route
        element={(
          <ProtectedRoute allowedRoles={["User", "Admin"]}>
            <AppShell
              isAdmin={isAdmin}
              userName={userName}
              onLogout={() => logout({ logoutParams: { returnTo: window.location.origin } })}
            />
          </ProtectedRoute>
        )}
      >
        <Route index element={<MonitoringPage />} />
        <Route
          path="admin"
          element={(
            <ProtectedRoute allowedRoles={["Admin"]}>
              <AdminPage />
            </ProtectedRoute>
          )}
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
