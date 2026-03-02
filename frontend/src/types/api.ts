export type DashboardSummary = {
  totalSpots: number;
  occupiedSpots: number;
  freeSpots: number;
  occupancyRate: number;
  lastTelemetryAtUtc: string | null;
};

export type SpotState = {
  id: number;
  deviceId: string;
  displayName: string;
  occupied: boolean;
  distanceCm: number | null;
  lastTelemetryAtUtc: string | null;
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

export type DashboardSnapshot = {
  generatedAtUtc: string;
  summary: DashboardSummary;
  spots: SpotState[];
};
