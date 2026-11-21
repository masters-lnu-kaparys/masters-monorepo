export type SpotDataStatus = "current" | "missing" | "stale";

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
  unknownSpots: number;
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
  unknownSpots: number;
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
  dataStatus: SpotDataStatus;
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
  unknownSpots: number;
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
  lastLatitude: number | null;
  lastLongitude: number | null;
  lastTelemetryAtUtc: string | null;
  dataStatus: SpotDataStatus;
};

export type AdminDetectedDevice = {
  dataStatus: SpotDataStatus;
  deviceId: string;
  firstSeenAtUtc: string;
  lastSeenAtUtc: string;
  lastMeasuredAtUtc: string;
  lastDistanceCm: number;
  lastOccupied: boolean;
  lastLatitude: number | null;
  lastLongitude: number | null;
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
  unknownSpots: number;
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

export const DEVICE_COMMAND = {
  PING: 1,
  MEASURE_NOW: 2,
  SET_THRESHOLDS: 3,
  REBOOT: 4,
} as const;

export type DeviceCommandType = (typeof DEVICE_COMMAND)[keyof typeof DEVICE_COMMAND];

export type SendDeviceCommandInput = {
  commandType: DeviceCommandType;
  occupiedBelowCm: number | null;
  freeAboveCm: number | null;
};

export type DeviceCommandResult = {
  deviceId: string;
  statusCode: number;
  responsePayload: string;
  processedAtUtc: string;
};
