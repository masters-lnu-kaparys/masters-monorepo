import { useAuth0 } from "@auth0/auth0-react";
import type { ReactElement } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { getEffectiveUserRoles } from "../auth/config";
import { useI18n } from "../i18n/LanguageProvider";
import { FullScreenStatus } from "./FullScreenStatus";

type ProtectedRouteProps = {
  children: ReactElement;
  allowedRoles?: string[];
};

export function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuth0();
  const { t } = useI18n();
  const location = useLocation();

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
        to="/login"
        replace
        state={{
          returnTo: `${location.pathname}${location.search}${location.hash}`,
        }}
      />
    );
  }

  if (allowedRoles && allowedRoles.length > 0) {
    const roles = getEffectiveUserRoles(user as Record<string, unknown> | undefined);
    const hasAccess = allowedRoles.some((role) => roles.includes(role));

    if (!hasAccess) {
      return <Navigate to="/forbidden" replace />;
    }
  }

  return children;
}
