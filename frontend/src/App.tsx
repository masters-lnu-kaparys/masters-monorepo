import { useAuth0 } from "@auth0/auth0-react";
import { useCallback, useLayoutEffect } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { configureApiClient, resetApiClient } from "./api/http";
import { APP_ROUTES } from "./app/routes";
import { AUTH_CALLBACK_PATH, hasAuthCallbackParams } from "./auth/config";
import { useEffectiveRoles } from "./auth/useEffectiveRoles";
import { AppShell } from "./components/AppShell";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { useI18n } from "./i18n/LanguageProvider";
import { AdminPage } from "./pages/AdminPage";
import { AuthCallbackPage } from "./pages/AuthCallbackPage";
import { ForbiddenPage } from "./pages/ForbiddenPage";
import { LoginPage } from "./pages/LoginPage";
import { MonitoringPage } from "./pages/MonitoringPage";
import "./App.css";

export default function App() {
  const { getAccessTokenSilently, logout, user } = useAuth0();
  const { t } = useI18n();
  const navigate = useNavigate();

  const { roles } = useEffectiveRoles();
  const isAdmin = roles.includes("Admin");
  const userName = user?.name ?? user?.email ?? user?.nickname ?? t("app.userFallbackName");

  const handleUnauthorized = useCallback(() => {
    if (window.location.pathname === APP_ROUTES.login || window.location.pathname === AUTH_CALLBACK_PATH) {
      return;
    }

    if (hasAuthCallbackParams(window.location.search)) {
      return;
    }

    navigate(APP_ROUTES.login, {
      replace: true,
      state: {
        returnTo: `${window.location.pathname}${window.location.search}${window.location.hash}`,
      },
    });
  }, [navigate]);

  const handleForbidden = useCallback(() => {
    navigate(APP_ROUTES.forbidden, { replace: true });
  }, [navigate]);

  useLayoutEffect(() => {
    configureApiClient({
      getAccessToken: getAccessTokenSilently,
      onUnauthorized: handleUnauthorized,
      onForbidden: handleForbidden,
    });

    return () => {
      resetApiClient();
    };
  }, [getAccessTokenSilently, handleForbidden, handleUnauthorized]);

  return (
    <Routes>
      <Route path={APP_ROUTES.login.slice(1)} element={<LoginPage />} />
      <Route path={APP_ROUTES.forbidden.slice(1)} element={<ForbiddenPage />} />
      <Route path={AUTH_CALLBACK_PATH.slice(1)} element={<AuthCallbackPage />} />
      <Route
        element={(
          <ProtectedRoute>
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
          path={APP_ROUTES.admin.slice(1)}
          element={(
            <ProtectedRoute allowedRoles={["Admin"]}>
              <AdminPage />
            </ProtectedRoute>
          )}
        />
      </Route>
      <Route path="*" element={<Navigate to={APP_ROUTES.home} replace />} />
    </Routes>
  );
}
