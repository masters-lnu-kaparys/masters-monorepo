import { getLocaleTag, getStoredLanguage } from "../i18n/config";
import { translate } from "../i18n/messages";

const DEFAULT_API_BASE_URL = "https://localhost:5001";
export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

type AccessTokenProvider = () => Promise<string>;

type ApiClientConfig = {
  getAccessToken: AccessTokenProvider;
  onUnauthorized?: () => void;
  onForbidden?: () => void;
};

type ProblemDetailsPayload = {
  title?: string;
  detail?: string;
  errors?: Record<string, string[]>;
};

let accessTokenProvider: AccessTokenProvider | null = null;
let unauthorizedHandler: (() => void) | undefined;
let forbiddenHandler: (() => void) | undefined;

function t(key: string, params?: Record<string, string | number>) {
  return translate(getStoredLanguage(), key, params);
}

async function resolveErrorMessage(response: Response): Promise<string | null> {
  const raw = (await response.text()).trim();

  if (!raw) {
    return null;
  }

  const contentType = response.headers.get("Content-Type") ?? "";

  if (contentType.includes("json")) {
    try {
      const payload = JSON.parse(raw) as ProblemDetailsPayload | string;

      if (typeof payload === "string") {
        return payload;
      }

      const validationMessage = payload.errors
        ? Object.values(payload.errors)
            .flat()
            .find((message) => Boolean(message))
        : undefined;

      return validationMessage ?? payload.detail ?? payload.title ?? raw;
    } catch {
      return raw;
    }
  }

  return raw;
}

export class ApiError extends Error {
  public readonly status: number;

  public constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function configureApiClient(config: ApiClientConfig) {
  accessTokenProvider = config.getAccessToken;
  unauthorizedHandler = config.onUnauthorized;
  forbiddenHandler = config.onForbidden;
}

export function resetApiClient() {
  accessTokenProvider = null;
  unauthorizedHandler = undefined;
  forbiddenHandler = undefined;
}

export async function requestAccessToken(): Promise<string> {
  if (!accessTokenProvider) {
    throw new Error(t("api.notConfigured"));
  }

  try {
    return await accessTokenProvider();
  } catch (error) {
    unauthorizedHandler?.();
    throw error;
  }
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await requestAccessToken();
  const headers = new Headers(init?.headers ?? {});
  headers.set("Accept", "application/json");
  headers.set("Accept-Language", getLocaleTag(getStoredLanguage()));
  headers.set("Authorization", `Bearer ${token}`);

  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers,
  });

  if (response.status === 401) {
    unauthorizedHandler?.();
    throw new ApiError((await resolveErrorMessage(response)) ?? t("api.unauthorized"), 401);
  }

  if (response.status === 403) {
    forbiddenHandler?.();
    throw new ApiError((await resolveErrorMessage(response)) ?? t("api.forbidden"), 403);
  }

  if (!response.ok) {
    const message = (await resolveErrorMessage(response)) ?? t("api.requestFailed", { status: response.status });
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function getJson<T>(path: string): Promise<T> {
  return requestJson<T>(path, { method: "GET" });
}

export async function postJson<TResponse, TRequest>(path: string, body: TRequest): Promise<TResponse> {
  return requestJson<TResponse>(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function putJson<TRequest>(path: string, body: TRequest): Promise<void> {
  await requestJson<void>(path, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function deleteJson(path: string): Promise<void> {
  await requestJson<void>(path, { method: "DELETE" });
}
