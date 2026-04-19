import { APP_ROUTES } from "../app/routes";

export const AUTH0_ROLE_CLAIM =
  import.meta.env.VITE_AUTH0_ROLE_CLAIM ?? "https://masters.api/roles";
export const AUTH_CALLBACK_PATH = APP_ROUTES.authCallback;

export type Auth0RuntimeConfig = {
  domain: string;
  clientId: string;
  audience: string;
  roleClaimType: string;
};

function readEnvValue(value: string | undefined): string | null {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

export function getAuth0RuntimeConfig(): Auth0RuntimeConfig | null {
  const domain = readEnvValue(import.meta.env.VITE_AUTH0_DOMAIN);
  const clientId = readEnvValue(import.meta.env.VITE_AUTH0_CLIENT_ID);
  const audience = readEnvValue(import.meta.env.VITE_AUTH0_AUDIENCE);

  if (!domain || !clientId || !audience) {
    return null;
  }

  return {
    domain,
    clientId,
    audience,
    roleClaimType: AUTH0_ROLE_CLAIM,
  };
}

export function readUserRoles(
  claims: Record<string, unknown> | undefined,
  roleClaimType = AUTH0_ROLE_CLAIM,
): string[] {
  const rawValue = claims?.[roleClaimType];

  if (Array.isArray(rawValue)) {
    return rawValue.filter((value): value is string => typeof value === "string");
  }

  if (typeof rawValue === "string") {
    return [rawValue];
  }

  return [];
}

export function getEffectiveUserRoles(
  claims: Record<string, unknown> | undefined,
  roleClaimType = AUTH0_ROLE_CLAIM,
): string[] {
  const explicitRoles = readUserRoles(claims, roleClaimType);

  if (explicitRoles.length > 0) {
    return explicitRoles;
  }

  return claims ? ["User"] : [];
}

export function hasAuthCallbackParams(search: string): boolean {
  const params = new URLSearchParams(search);
  return params.has("code") && params.has("state");
}
