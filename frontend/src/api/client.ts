import type {
  AdminDetectedDevice,
  AdminParkingLot,
  MapOverview,
  SpotHistory,
  UpsertParkingLotInput,
  UpsertParkingSpotInput,
} from "../types/api";
import { deleteJson, getJson, postJson, putJson } from "./http";

export async function fetchMapOverview(): Promise<MapOverview> {
  return getJson<MapOverview>("/api/map/overview");
}

export async function fetchLotDetails(lotId: number) {
  return getJson(`/api/lots/${lotId}`);
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

export async function fetchAdminLots(): Promise<AdminParkingLot[]> {
  return getJson<AdminParkingLot[]>("/api/admin/lots");
}

export async function fetchAdminDetectedDevices(): Promise<AdminDetectedDevice[]> {
  return getJson<AdminDetectedDevice[]>("/api/admin/devices/unassigned");
}

export async function createAdminLot(input: UpsertParkingLotInput): Promise<number> {
  return postJson<number, UpsertParkingLotInput>("/api/admin/lots", input);
}

export async function updateAdminLot(lotId: number, input: UpsertParkingLotInput): Promise<void> {
  await putJson(`/api/admin/lots/${lotId}`, input);
}

export async function deleteAdminLot(lotId: number): Promise<void> {
  await deleteJson(`/api/admin/lots/${lotId}`);
}

export async function createAdminSpot(lotId: number, input: UpsertParkingSpotInput): Promise<number> {
  return postJson<number, UpsertParkingSpotInput>(`/api/admin/lots/${lotId}/spots`, input);
}

export async function updateAdminSpot(spotId: number, input: UpsertParkingSpotInput): Promise<void> {
  await putJson(`/api/admin/spots/${spotId}`, input);
}

export async function deleteAdminSpot(spotId: number): Promise<void> {
  await deleteJson(`/api/admin/spots/${spotId}`);
}
