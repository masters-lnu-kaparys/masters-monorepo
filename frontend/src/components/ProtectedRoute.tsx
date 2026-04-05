import { useAuth0 } from "@auth0/auth0-react";
import type { ReactElement } from "react";
import { useEffect, useRef } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { readUserRoles } from "../auth/config";
import { FullScreenStatus } from "./FullScreenStatus";

type ProtectedRouteProps = {
  children: ReactElement;
  allowedRoles?: string[];
};

export function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, loginWithRedirect, user } = useAuth0();
  const location = useLocation();
  const redirectTriggered = useRef(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated && !redirectTriggered.current) {
      redirectTriggered.current = true;
      void loginWithRedirect({
        appState: {
          returnTo: `${location.pathname}${location.search}${location.hash}`,
        },
      });
    }
  }, [isAuthenticated, isLoading, location.hash, location.pathname, location.search, loginWithRedirect]);

  if (isLoading || !isAuthenticated) {
    return (
      <FullScreenStatus
        title="Підключаємо ваш обліковий запис"
        description="Застосунок перевіряє активну сесію і готує безпечний доступ до карти та адмінки."
        loading
      />
    );
  }

  if (allowedRoles && allowedRoles.length > 0) {
    const roles = readUserRoles(user as Record<string, unknown> | undefined);
    const hasAccess = allowedRoles.some((role) => roles.includes(role));

    if (!hasAccess) {
      return <Navigate to="/forbidden" replace />;
    }
  }

  return children;
}
