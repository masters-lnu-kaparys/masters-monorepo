import type { DashboardSummary, SpotHistory, SpotState } from "../types/api";

const DEFAULT_API_BASE_URL = "https://localhost:5001";
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }

  return (await response.json()) as T;
}

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  return getJson<DashboardSummary>("/api/dashboard/summary");
}

export async function fetchSpots(): Promise<SpotState[]> {
  return getJson<SpotState[]>("/api/spots");
}

export async function fetchSpotHistory(
  spotId: number,
  options?: {
    fromUtc?: string;
    toUtc?: string;
    maxPoints?: number;
  },
): Promise<SpotHistory> {
  const queryParams = new URLSearchParams();

  if (options?.fromUtc) {
    queryParams.set("fromUtc", options.fromUtc);
  }

  if (options?.toUtc) {
    queryParams.set("toUtc", options.toUtc);
  }

  if (options?.maxPoints) {
    queryParams.set("maxPoints", String(options.maxPoints));
  }

  const query = queryParams.toString();
  const suffix = query.length > 0 ? `?${query}` : "";

  return getJson<SpotHistory>(`/api/spots/${spotId}/history${suffix}`);
}

export { apiBaseUrl };
