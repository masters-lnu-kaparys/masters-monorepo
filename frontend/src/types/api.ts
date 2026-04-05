export const SPOT_SOURCE = {
  REAL: 1,
  SIMULATED: 2,
} as const;

export type SpotSourceKind = (typeof SPOT_SOURCE)[keyof typeof SPOT_SOURCE];

export type MapCenter = {
  latitude: number;
  longitude: number;
};

export type MapSummary = {
  totalLots: number;
  totalSpots: number;
  occupiedSpots: number;
  freeSpots: number;
  occupancyRate: number;
  lastUpdatedAtUtc: string | null;
};

export type ParkingLotMap = {
  id: number;
  name: string;
  city: string;
  address: string;
  latitude: number;
  longitude: number;
  totalSpots: number;
  occupiedSpots: number;
  freeSpots: number;
  occupancyRate: number;
  lastUpdatedAtUtc: string | null;
};

export type MapOverview = {
  mapCenter: MapCenter;
  zoom: number;
  city: string;
  userLocationMaxDistanceKm: number;
  summary: MapSummary;
  lots: ParkingLotMap[];
};

export type LotSpotState = {
  id: number;
  deviceId: string;
  displayName: string;
  occupied: boolean;
  distanceCm: number | null;
  lastUpdatedAtUtc: string | null;
};

export type LotActivity = {
  spotId: number;
  spotName: string;
  occupied: boolean;
  distanceCm: number;
  measuredAtUtc: string;
};

export type LotDetails = {
  id: number;
  name: string;
  city: string;
  address: string;
  latitude: number;
  longitude: number;
  totalSpots: number;
  occupiedSpots: number;
  freeSpots: number;
  occupancyRate: number;
  lastUpdatedAtUtc: string | null;
  spots: LotSpotState[];
  recentActivity: LotActivity[];
};

export type SpotHistoryPoint = {
  measuredAtUtc: string;
  distanceCm: number;
  occupied: boolean;
};

export type SpotHistory = {
  spotId: number;
  fromUtc: string;
  toUtc: string;
  points: SpotHistoryPoint[];
};

export type MapSnapshot = {
  generatedAtUtc: string;
  summary: MapSummary;
  lots: ParkingLotMap[];
};

export type AdminParkingSpot = {
  id: number;
  displayName: string;
  deviceId: string;
  sourceKind: SpotSourceKind;
  occupied: boolean;
  distanceCm: number | null;
  lastTelemetryAtUtc: string | null;
};

export type AdminParkingLot = {
  id: number;
  name: string;
  city: string;
  address: string;
  latitude: number;
  longitude: number;
  totalSpots: number;
  occupiedSpots: number;
  freeSpots: number;
  spots: AdminParkingSpot[];
};

export type UpsertParkingLotInput = {
  name: string;
  city: string;
  address: string;
  latitude: number;
  longitude: number;
};

export type UpsertParkingSpotInput = {
  displayName: string;
  sourceKind: SpotSourceKind;
  deviceId: string | null;
};
