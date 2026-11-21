import { useAuth0 } from "@auth0/auth0-react";
import { lazy, Suspense, useCallback, useLayoutEffect } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { configureApiClient, resetApiClient } from "./api/http";
import { APP_ROUTES } from "./app/routes";
import { AUTH_CALLBACK_PATH, hasAuthCallbackParams } from "./auth/config";
import { useEffectiveRoles } from "./auth/useEffectiveRoles";
import { AppShell } from "./components/AppShell";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { useI18n } from "./i18n/context";
import { FullScreenStatus } from "./components/FullScreenStatus";
import { AuthCallbackPage } from "./pages/AuthCallbackPage";
import { ForbiddenPage } from "./pages/ForbiddenPage";
import { LoginPage } from "./pages/LoginPage";
import "./App.css";

const AdminPage = lazy(() => import("./pages/AdminPage").then(module => ({ default: module.AdminPage })));
const MonitoringPage = lazy(() => import("./pages/MonitoringPage").then(module => ({ default: module.MonitoringPage })));

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
      getAccessToken: async () => {
        const token = await getAccessTokenSilently();
        if (!token) throw new Error(t("api.unauthorized"));
        return token;
      },
      onUnauthorized: handleUnauthorized,
      onForbidden: handleForbidden,
    });

    return () => {
      resetApiClient();
    };
  }, [getAccessTokenSilently, handleForbidden, handleUnauthorized, t]);

  return (
    <Suspense fallback={<FullScreenStatus titleKey="route.loading.title" descriptionKey="route.loading.description" loading />}><Routes>
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
    </Routes></Suspense>
  );
}
