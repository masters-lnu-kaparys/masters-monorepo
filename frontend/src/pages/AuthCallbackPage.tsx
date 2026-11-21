import { useAuth0 } from "@auth0/auth0-react";
import { Navigate } from "react-router-dom";
import { APP_ROUTES } from "../app/routes";
import { FullScreenStatus } from "../components/FullScreenStatus";
import { AUTH_CALLBACK_PATH, hasAuthCallbackParams } from "../auth/config";
import { useI18n } from "../i18n/context";

type AuthCallbackPageProps = {
  fallbackTo?: string;
};

export function AuthCallbackPage({ fallbackTo = "/" }: AuthCallbackPageProps) {
  const { error, isAuthenticated, isLoading } = useAuth0();
  const { t } = useI18n();
  const isCallbackUrl = hasAuthCallbackParams(window.location.search)
    || window.location.pathname === AUTH_CALLBACK_PATH;

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

  if (isLoading || (isCallbackUrl && !isAuthenticated)) {
    return (
      <FullScreenStatus
        title={t("auth.callback.loadingTitle")}
        description={t("auth.callback.loadingDescription")}
        loading
      />
    );
  }

  if (isAuthenticated) {
    return <Navigate to={fallbackTo} replace />;
  }

  return <Navigate to={APP_ROUTES.login} replace />;
}
