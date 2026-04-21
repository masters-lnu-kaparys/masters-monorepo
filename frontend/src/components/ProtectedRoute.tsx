import { useAuth0 } from "@auth0/auth0-react";
import type { ReactElement } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { APP_ROUTES } from "../app/routes";
import { hasAuthCallbackParams } from "../auth/config";
import { useEffectiveRoles } from "../auth/useEffectiveRoles";
import { useI18n } from "../i18n/LanguageProvider";
import { AuthCallbackPage } from "../pages/AuthCallbackPage";
import { FullScreenStatus } from "./FullScreenStatus";

type ProtectedRouteProps = {
  children: ReactElement;
  allowedRoles?: string[];
};

export function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { error, isAuthenticated, isLoading } = useAuth0();
  const { roles, isResolvingRoles } = useEffectiveRoles();
  const { t } = useI18n();
  const location = useLocation();
  const waitingForAuthCallback = hasAuthCallbackParams(location.search);

  if (error) {
    return (
      <FullScreenStatus
        title={t("auth.callback.errorTitle")}
        description={t("auth.callback.errorDescription")}
        severity="error"
        actionLabel={t("auth.callback.backToLogin")}
        onAction={() => {
          window.location.assign(APP_ROUTES.login);
        }}
      />
    );
  }

  if (waitingForAuthCallback) {
    return <AuthCallbackPage fallbackTo={location.pathname} />;
  }

  if (isLoading) {
    return (
      <FullScreenStatus
        title={t("route.loading.title")}
        description={t("route.loading.description")}
        loading
      />
    );
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to={APP_ROUTES.login}
        replace
        state={{
          returnTo: `${location.pathname}${location.search}${location.hash}`,
        }}
      />
    );
  }

  if (allowedRoles && allowedRoles.length > 0) {
    if (isResolvingRoles) {
      return (
        <FullScreenStatus
          title={t("route.loading.title")}
          description={t("route.loading.description")}
          loading
        />
      );
    }

    const hasAccess = allowedRoles.some((role) => roles.includes(role));

    if (!hasAccess) {
      return <Navigate to={APP_ROUTES.forbidden} replace />;
    }
  }

  return children;
}
