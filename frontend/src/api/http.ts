const DEFAULT_API_BASE_URL = "https://localhost:5001";
export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

type AccessTokenProvider = () => Promise<string>;

type ApiClientConfig = {
  getAccessToken: AccessTokenProvider;
  onUnauthorized?: () => void;
  onForbidden?: () => void;
};

let accessTokenProvider: AccessTokenProvider | null = null;
let unauthorizedHandler: (() => void) | undefined;
let forbiddenHandler: (() => void) | undefined;

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
    throw new Error("The API client is not configured with an access token provider.");
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
    throw new ApiError("The session has expired. Please sign in again.", 401);
  }

  if (response.status === 403) {
    forbiddenHandler?.();
    throw new ApiError("You do not have permission to perform this action.", 403);
  }

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(text || `Request failed with status ${response.status}.`, response.status);
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
