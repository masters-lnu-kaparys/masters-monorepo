import { Fragment, useEffect, useMemo } from "react";
import { Box, Paper, Stack, Typography } from "@mui/material";
import type { LatLngBoundsExpression, LatLngExpression } from "leaflet";
import { Circle, CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import type { AdminDetectedDevice, AdminParkingLot } from "../types/api";
import { SPOT_SOURCE } from "../types/api";
import { useI18n } from "../i18n/context";

const DEVICE_ZONE_RADIUS_KM = 0.2;
const DEVICE_ZONE_RADIUS_METERS = DEVICE_ZONE_RADIUS_KM * 1000;

type AdminDeviceMapProps = {
  lots: AdminParkingLot[];
  detectedDevices: AdminDetectedDevice[];
  selectedLotId: number | null;
  locale: string;
};

type DeviceMarkerState = "linked" | "outsideAssignedLot" | "unassignedNearby" | "outOfRange";

type AdminDeviceMarker = {
  key: string;
  deviceId: string;
  label: string;
  latitude: number;
  longitude: number;
  occupied: boolean;
  distanceCm: number | null;
  lastSeenAtUtc: string | null;
  state: DeviceMarkerState;
  assignedLotName: string | null;
  nearestLotName: string | null;
  nearestDistanceKm: number | null;
};

function degreesToRadians(value: number) {
  return value * (Math.PI / 180);
}

function calculateDistanceKm(
  latitudeA: number,
  longitudeA: number,
  latitudeB: number,
  longitudeB: number,
) {
  const earthRadiusKm = 6371;
  const deltaLatitude = degreesToRadians(latitudeB - latitudeA);
  const deltaLongitude = degreesToRadians(longitudeB - longitudeA);
  const latitudeARadians = degreesToRadians(latitudeA);
  const latitudeBRadians = degreesToRadians(latitudeB);

  const haversine = Math.sin(deltaLatitude / 2) * Math.sin(deltaLatitude / 2)
    + Math.cos(latitudeARadians) * Math.cos(latitudeBRadians)
    * Math.sin(deltaLongitude / 2) * Math.sin(deltaLongitude / 2);

  const arc = 2 * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine));
  return earthRadiusKm * arc;
}

function resolveNearestLot(
  lots: AdminParkingLot[],
  latitude: number,
  longitude: number,
) {
  return lots
    .map((lot) => ({
      lot,
      distanceKm: calculateDistanceKm(latitude, longitude, lot.latitude, lot.longitude),
    }))
    .sort((left, right) => left.distanceKm - right.distanceKm)[0] ?? null;
}

function formatDateTime(value: string | null, locale: string, fallback: string) {
  if (!value) {
    return fallback;
  }

  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function MapViewport({ points }: { points: LatLngExpression[] }) {
  const map = useMap();

  useEffect(() => {
    map.invalidateSize();

    if (points.length === 0) {
      map.setView([49.8419, 24.0315], 12);
      return;
    }

    if (points.length === 1) {
      map.setView(points[0], 14);
      return;
    }

    map.fitBounds(points as LatLngBoundsExpression, { padding: [36, 36] });
  }, [map, points]);

  return null;
}

function legendColor(state: DeviceMarkerState) {
  switch (state) {
    case "linked":
      return "#116149";
    case "outsideAssignedLot":
      return "#d97706";
    case "unassignedNearby":
      return "#2563eb";
    case "outOfRange":
      return "#c2410c";
    default:
      return "#6b7280";
  }
}

export function AdminDeviceMap({ lots, detectedDevices, selectedLotId, locale }: AdminDeviceMapProps) {
  const { t } = useI18n();

  const linkedDevices = useMemo<AdminDeviceMarker[]>(() => {
    return lots.flatMap((lot) => lot.spots
      .filter((spot) => spot.sourceKind === SPOT_SOURCE.REAL && spot.lastLatitude !== null && spot.lastLongitude !== null)
      .map((spot) => {
        const nearestDistanceKm = calculateDistanceKm(
          spot.lastLatitude!,
          spot.lastLongitude!,
          lot.latitude,
          lot.longitude,
        );

        return {
          key: `spot-${spot.id}`,
          deviceId: spot.deviceId,
          label: spot.displayName,
          latitude: spot.lastLatitude!,
          longitude: spot.lastLongitude!,
          occupied: spot.occupied,
          distanceCm: spot.distanceCm,
          lastSeenAtUtc: spot.lastTelemetryAtUtc,
          state: nearestDistanceKm > DEVICE_ZONE_RADIUS_KM ? "outsideAssignedLot" : "linked",
          assignedLotName: lot.name,
          nearestLotName: lot.name,
          nearestDistanceKm,
        } satisfies AdminDeviceMarker;
      }));
  }, [lots]);

  const unassignedDevices = useMemo<AdminDeviceMarker[]>(() => {
    return detectedDevices
      .filter((device) => device.lastLatitude !== null && device.lastLongitude !== null)
      .map((device) => {
        const nearest = resolveNearestLot(lots, device.lastLatitude!, device.lastLongitude!);

        return {
          key: `detected-${device.deviceId}`,
          deviceId: device.deviceId,
          label: device.deviceId,
          latitude: device.lastLatitude!,
          longitude: device.lastLongitude!,
          occupied: device.lastOccupied,
          distanceCm: device.lastDistanceCm,
          lastSeenAtUtc: device.lastSeenAtUtc,
          state: nearest && nearest.distanceKm <= DEVICE_ZONE_RADIUS_KM ? "unassignedNearby" : "outOfRange",
          assignedLotName: null,
          nearestLotName: nearest?.lot.name ?? null,
          nearestDistanceKm: nearest?.distanceKm ?? null,
        } satisfies AdminDeviceMarker;
      });
  }, [detectedDevices, lots]);

  const deviceMarkers = useMemo(
    () => [...linkedDevices, ...unassignedDevices],
    [linkedDevices, unassignedDevices],
  );

  const points = useMemo<LatLngExpression[]>(
    () => [
      ...lots.map((lot) => [lot.latitude, lot.longitude] as LatLngExpression),
      ...deviceMarkers.map((device) => [device.latitude, device.longitude] as LatLngExpression),
    ],
    [deviceMarkers, lots],
  );

  const numberFormatter = useMemo(
    () => new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }),
    [locale],
  );

  const statusCounts = useMemo(() => ({
    linked: linkedDevices.filter((device) => device.state === "linked").length,
    outsideAssignedLot: linkedDevices.filter((device) => device.state === "outsideAssignedLot").length,
    unassignedNearby: unassignedDevices.filter((device) => device.state === "unassignedNearby").length,
    outOfRange: unassignedDevices.filter((device) => device.state === "outOfRange").length,
  }), [linkedDevices, unassignedDevices]);

  const missingCoordinatesCount = useMemo(() => (
    lots.flatMap((lot) => lot.spots)
      .filter((spot) => spot.sourceKind === SPOT_SOURCE.REAL && (spot.lastLatitude === null || spot.lastLongitude === null))
      .length
    + detectedDevices.filter((device) => device.lastLatitude === null || device.lastLongitude === null).length
  ), [detectedDevices, lots]);

  return (
    <Paper sx={{ p: 2.5, borderRadius: 6, border: "1px solid rgba(17, 97, 73, 0.12)" }}>
      <Stack spacing={2}>
        <Box>
          <Typography variant="h5" sx={{ mb: 0.5 }}>
            {t("admin.deviceMap.title")}
          </Typography>
          <Typography color="text.secondary">
            {t("admin.deviceMap.description")}
          </Typography>
        </Box>

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "repeat(2, minmax(0, 1fr))", xl: "repeat(4, minmax(0, 1fr))" },
            gap: 1.25,
          }}
        >
          <Paper elevation={0} sx={{ p: 1.5, borderRadius: 4, bgcolor: "rgba(17,97,73,0.06)", border: "1px solid rgba(17, 97, 73, 0.08)" }}>
            <Typography variant="overline" color="text.secondary">{t("admin.deviceMap.counts.linked")}</Typography>
            <Typography variant="h4" fontWeight={800}>{statusCounts.linked}</Typography>
          </Paper>
          <Paper elevation={0} sx={{ p: 1.5, borderRadius: 4, bgcolor: "rgba(217,119,6,0.08)", border: "1px solid rgba(217, 119, 6, 0.12)" }}>
            <Typography variant="overline" color="text.secondary">{t("admin.deviceMap.counts.outsideAssignedLot")}</Typography>
            <Typography variant="h4" fontWeight={800}>{statusCounts.outsideAssignedLot}</Typography>
          </Paper>
          <Paper elevation={0} sx={{ p: 1.5, borderRadius: 4, bgcolor: "rgba(37,99,235,0.08)", border: "1px solid rgba(37, 99, 235, 0.12)" }}>
            <Typography variant="overline" color="text.secondary">{t("admin.deviceMap.counts.unassignedNearby")}</Typography>
            <Typography variant="h4" fontWeight={800}>{statusCounts.unassignedNearby}</Typography>
          </Paper>
          <Paper elevation={0} sx={{ p: 1.5, borderRadius: 4, bgcolor: "rgba(194,65,12,0.08)", border: "1px solid rgba(194, 65, 12, 0.12)" }}>
            <Typography variant="overline" color="text.secondary">{t("admin.deviceMap.counts.outOfRange")}</Typography>
            <Typography variant="h4" fontWeight={800}>{statusCounts.outOfRange}</Typography>
          </Paper>
        </Box>

        {missingCoordinatesCount > 0 ? (
          <Typography variant="body2" color="text.secondary">
            {t("admin.deviceMap.missingCoordinates", { count: missingCoordinatesCount })}
          </Typography>
        ) : null}

        <Box sx={{ height: 420, borderRadius: 4, overflow: "hidden", border: "1px solid rgba(17, 97, 73, 0.12)" }}>
          <MapContainer center={[49.8419, 24.0315]} zoom={12} style={{ height: "100%", width: "100%" }}>
            <MapViewport points={points} />
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {lots.map((lot) => {
              const selected = lot.id === selectedLotId;
              const color = selected ? "#d97706" : "#116149";

              return (
                <Fragment key={`lot-${lot.id}`}>
                  <Circle
                    center={[lot.latitude, lot.longitude]}
                    radius={DEVICE_ZONE_RADIUS_METERS}
                    pathOptions={{
                      color,
                      weight: selected ? 2.5 : 1.5,
                      fillColor: color,
                      fillOpacity: selected ? 0.12 : 0.06,
                    }}
                  />
                  <CircleMarker
                    center={[lot.latitude, lot.longitude]}
                    radius={selected ? 10 : 8}
                    pathOptions={{
                      color,
                      weight: 2,
                      fillColor: "#fffdf7",
                      fillOpacity: 1,
                    }}
                  >
                    <Popup>
                      <Stack spacing={0.5}>
                        <Typography fontWeight={800}>{lot.name}</Typography>
                        <Typography variant="body2">{lot.address}, {lot.city}</Typography>
                        <Typography variant="body2" color="text.secondary">
                          {t("admin.lotAvailability", { free: lot.freeSpots, total: lot.totalSpots })}
                        </Typography>
                      </Stack>
                    </Popup>
                  </CircleMarker>
                </Fragment>
              );
            })}

            {deviceMarkers.map((device) => (
              <CircleMarker
                key={device.key}
                center={[device.latitude, device.longitude]}
                radius={7}
                pathOptions={{
                  color: legendColor(device.state),
                  weight: 2,
                  fillColor: legendColor(device.state),
                  fillOpacity: 0.85,
                }}
              >
                <Popup>
                  <Stack spacing={0.5}>
                    <Typography fontWeight={800}>{device.label}</Typography>
                    <Typography variant="body2">{t("common.deviceId")}: {device.deviceId}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {t(`admin.deviceMap.state.${device.state}`)}
                    </Typography>
                    {device.assignedLotName ? (
                      <Typography variant="body2" color="text.secondary">
                        {t("admin.deviceMap.assignedLot", { name: device.assignedLotName })}
                      </Typography>
                    ) : null}
                    {device.nearestLotName && device.nearestDistanceKm !== null ? (
                      <Typography variant="body2" color="text.secondary">
                        {t("admin.deviceMap.nearestLot", {
                          name: device.nearestLotName,
                          distance: numberFormatter.format(device.nearestDistanceKm),
                        })}
                      </Typography>
                    ) : null}
                    {device.distanceCm !== null ? (
                      <Typography variant="body2" color="text.secondary">
                        {t("admin.detectedDevices.lastMeasurement", {
                          distance: numberFormatter.format(device.distanceCm),
                        })}
                      </Typography>
                    ) : null}
                    <Typography variant="body2" color="text.secondary">
                      {t("admin.detectedDevices.lastSeen", {
                        value: formatDateTime(device.lastSeenAtUtc, locale, t("common.noDataYet")),
                      })}
                    </Typography>
                  </Stack>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </Box>

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
            gap: 1,
          }}
        >
          {(["linked", "outsideAssignedLot", "unassignedNearby", "outOfRange"] as DeviceMarkerState[]).map((state) => (
            <Stack key={state} direction="row" spacing={1} alignItems="center">
              <Box
                sx={{
                  width: 12,
                  height: 12,
                  borderRadius: "999px",
                  bgcolor: legendColor(state),
                }}
              />
              <Typography variant="body2" color="text.secondary">
                {t(`admin.deviceMap.state.${state}`)}
              </Typography>
            </Stack>
          ))}
        </Box>
      </Stack>
    </Paper>
  );
}
