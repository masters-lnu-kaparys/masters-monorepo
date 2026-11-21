import { useAuth0 } from "@auth0/auth0-react";
import { useEffect, useMemo, useState } from "react";
import { getEffectiveUserRoles, readUserRoles } from "./config";

function decodeJwtPayload(token: string): Record<string, unknown> | undefined {
  const parts = token.split(".");

  if (parts.length < 2) {
    return undefined;
  }

  try {
    const base64 = parts[1]
      .replace(/-/g, "+")
      .replace(/_/g, "/")
      .padEnd(Math.ceil(parts[1].length / 4) * 4, "=");

    const json = decodeURIComponent(
      atob(base64)
        .split("")
        .map((char) => `%${char.charCodeAt(0).toString(16).padStart(2, "0")}`)
        .join(""),
    );

    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return undefined;
  }
}

export function useEffectiveRoles() {
  const { getAccessTokenSilently, isAuthenticated, isLoading, user } = useAuth0();
  const explicitRoles = useMemo(
    () => readUserRoles(user as Record<string, unknown> | undefined),
    [user],
  );
  const [resolvedToken, setResolvedToken] = useState<{ subject: string; roles: string[] } | null>(null);
  const subject = isAuthenticated ? user?.sub ?? null : null;
  const tokenRoles = resolvedToken?.subject === subject ? resolvedToken?.roles ?? null : null;

  useEffect(() => {
    let active = true;

    if (!subject || explicitRoles.length > 0) return;

    void getAccessTokenSilently()
      .then((token) => {
        if (!active) {
          return;
        }

        const claims = token ? decodeJwtPayload(token) : undefined;
        const roles = readUserRoles(claims);
        setResolvedToken({ subject, roles });
      })
      .catch(() => {
        if (active) {
          setResolvedToken({ subject, roles: [] });
        }
      });

    return () => {
      active = false;
    };
  }, [explicitRoles, getAccessTokenSilently, subject]);

  const roles = useMemo(() => {
    if (explicitRoles.length > 0) {
      return explicitRoles;
    }

    if (tokenRoles && tokenRoles.length > 0) {
      return tokenRoles;
    }

    return getEffectiveUserRoles(user as Record<string, unknown> | undefined);
  }, [explicitRoles, tokenRoles, user]);

  const isResolvingRoles = isAuthenticated && explicitRoles.length === 0 && tokenRoles === null && !isLoading;

  return {
    roles,
    isResolvingRoles,
  };
}
