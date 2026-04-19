import ExploreRoundedIcon from "@mui/icons-material/ExploreRounded";
import LocationSearchingRoundedIcon from "@mui/icons-material/LocationSearchingRounded";
import LocalParkingRoundedIcon from "@mui/icons-material/LocalParkingRounded";
import PlaceRoundedIcon from "@mui/icons-material/PlaceRounded";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import RouteRoundedIcon from "@mui/icons-material/RouteRounded";
import SensorsRoundedIcon from "@mui/icons-material/SensorsRounded";
import TrafficRoundedIcon from "@mui/icons-material/TrafficRounded";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Container,
  Divider,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import { HubConnectionBuilder, LogLevel } from "@microsoft/signalr";
import type { LatLngExpression } from "leaflet";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { CircleMarker, MapContainer, TileLayer, useMap, ZoomControl } from "react-leaflet";
import { fetchLotDetails, fetchMapOverview, fetchSpotHistory } from "../api/client";
import { apiBaseUrl, requestAccessToken } from "../api/http";
import { DistanceHistoryChart } from "../components/DistanceHistoryChart";
import { useI18n } from "../i18n/LanguageProvider";
import type { LotDetails, MapOverview, MapSnapshot, SpotHistory } from "../types/api";

type LiveConnectionState = "connecting" | "connected" | "disconnected";
type GeolocationState = "idle" | "searching" | "resolved" | "fallback" | "denied" | "unsupported";
type MapViewState = {
  center: [number, number];
  zoom: number;
};

type TranslationFn = (key: string, params?: Record<string, string | number>) => string;

function MapViewUpdater({ center, zoom }: MapViewState) {
  const map = useMap();

  useEffect(() => {
    map.setView(center, zoom, {
      animate: true,
    });
  }, [center, map, zoom]);

  return null;
}

function SummaryCard({
  title,
  value,
  icon,
  compact = false,
  valueVariant = "default",
}: {
  title: string;
  value: string;
  icon: ReactNode;
  compact?: boolean;
  valueVariant?: "default" | "text";
}) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: compact ? 1.5 : 2,
        minHeight: compact ? 92 : 108,
        borderRadius: "12px",
        border: "1px solid rgba(17, 97, 73, 0.10)",
        bgcolor: "rgba(255, 253, 247, 0.92)",
        backdropFilter: "blur(12px)",
      }}
    >
      <Stack spacing={compact ? 1.1 : 1.5}>
        <Box
          sx={{
            width: compact ? 34 : 38,
            height: compact ? 34 : 38,
            borderRadius: "10px",
            display: "grid",
            placeItems: "center",
            color: "primary.main",
            bgcolor: "rgba(17, 97, 73, 0.1)",
            flexShrink: 0,
          }}
        >
          {icon}
        </Box>

        <Box sx={{ minWidth: 0 }}>
          <Typography
            variant="overline"
            color="text.secondary"
            sx={{
              display: "block",
              lineHeight: 1.15,
              letterSpacing: "0.08em",
              mb: compact ? 0.5 : 0.75,
              fontSize: compact ? "0.62rem" : undefined,
            }}
          >
            {title}
          </Typography>
          <Typography
            variant={valueVariant === "text" ? "h6" : "h4"}
            fontWeight={valueVariant === "text" ? 700 : 800}
            sx={{
              lineHeight: valueVariant === "text" ? 1.15 : 1.05,
              fontSize: valueVariant === "text"
                ? { xs: "1rem", sm: compact ? "1.1rem" : "1.2rem" }
                : undefined,
              wordBreak: "break-word",
              overflowWrap: "anywhere",
            }}
          >
            {value}
          </Typography>
        </Box>
      </Stack>
    </Paper>
  );
}

function LiveStateChip({ state }: { state: LiveConnectionState }) {
  const { t } = useI18n();
  const config = state === "connected"
    ? {
        label: t("monitoring.live.connected"),
        color: "#116149",
        background: "rgba(17, 97, 73, 0.10)",
      }
    : state === "connecting"
      ? {
          label: t("monitoring.live.connecting"),
          color: "#d97706",
          background: "rgba(217, 119, 6, 0.10)",
        }
      : {
          label: t("monitoring.live.disconnected"),
          color: "#475569",
          background: "rgba(100, 116, 139, 0.10)",
        };

  return (
    <Box
      sx={{
        display: "inline-flex",
        alignItems: "center",
        gap: 1,
        px: 1.5,
        py: 1,
        borderRadius: "8px",
        border: "1px solid rgba(17, 97, 73, 0.10)",
        bgcolor: config.background,
        color: config.color,
        fontWeight: 700,
      }}
    >
      <SensorsRoundedIcon fontSize="small" />
      <Typography variant="body2" sx={{ color: "inherit", fontWeight: 700 }}>
        {config.label}
      </Typography>
    </Box>
  );
}

function SpotStatusChip({ occupied }: { occupied: boolean }) {
  const { t } = useI18n();
  const config = occupied
    ? {
        label: t("monitoring.status.occupied"),
        color: "#b45309",
        background: "rgba(217, 119, 6, 0.12)",
      }
    : {
        label: t("monitoring.status.free"),
        color: "#116149",
        background: "rgba(17, 97, 73, 0.12)",
      };

  return (
    <Box
      sx={{
        minWidth: 88,
        px: 1.5,
        py: 0.75,
        borderRadius: "8px",
        textAlign: "center",
        fontSize: 14,
        fontWeight: 700,
        lineHeight: 1,
        color: config.color,
        bgcolor: config.background,
      }}
    >
      {config.label}
    </Box>
  );
}

function formatUpdateLabel(utc: string | null, locale: string, t: TranslationFn): string {
  if (!utc) {
    return t("common.noDataYet");
  }

  const measuredAt = new Date(utc).getTime();
  const diffSeconds = Math.round((measuredAt - Date.now()) / 1000);

  if (Math.abs(diffSeconds) <= 60) {
    return t("common.justNow");
  }

  const relativeTimeFormat = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });

  if (Math.abs(diffSeconds) < 3600) {
    return relativeTimeFormat.format(Math.round(diffSeconds / 60), "minute");
  }

  if (Math.abs(diffSeconds) < 86400) {
    return relativeTimeFormat.format(Math.round(diffSeconds / 3600), "hour");
  }

  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(utc));
}

function formatDateTime(utc: string | null, locale: string, t: TranslationFn): string {
  if (!utc) {
    return t("common.noUpdates");
  }

  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(utc));
}

function occupancyColor(occupancyRate: number): string {
  if (occupancyRate >= 0.8) {
    return "#c2410c";
  }

  if (occupancyRate >= 0.55) {
    return "#d97706";
  }

  return "#116149";
}

function haversineDistanceKm(a: [number, number], b: [number, number]): number {
  const toRadians = (value: number) => (value * Math.PI) / 180;
  const earthRadiusKm = 6371;
  const dLat = toRadians(b[0] - a[0]);
  const dLon = toRadians(b[1] - a[1]);
  const lat1 = toRadians(a[0]);
  const lat2 = toRadians(b[0]);

  const haversine =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) * Math.sin(dLon / 2);

  return 2 * earthRadiusKm * Math.asin(Math.sqrt(haversine));
}

function describeLocationMode(
  state: GeolocationState,
  city: string | null,
  fallbackCity: string,
  t: TranslationFn,
) {
  const cityLabel = city && city.trim().length > 0 ? city : fallbackCity;

  switch (state) {
    case "resolved":
      return t("monitoring.location.resolved");
    case "denied":
      return t("monitoring.location.denied", { city: cityLabel });
    case "unsupported":
      return t("monitoring.location.unsupported", { city: cityLabel });
    case "fallback":
      return t("monitoring.location.fallback", { city: cityLabel });
    case "searching":
      return t("monitoring.location.searching");
    default:
      return t("monitoring.location.default", { city: cityLabel });
  }
}

export function MonitoringPage() {
  const { t, language, locale } = useI18n();
  const [overview, setOverview] = useState<MapOverview | null>(null);
  const [selectedLotId, setSelectedLotId] = useState<number | null>(null);
  const [lotDetails, setLotDetails] = useState<LotDetails | null>(null);
  const [selectedSpotId, setSelectedSpotId] = useState<number | null>(null);
  const [history, setHistory] = useState<SpotHistory | null>(null);
  const [loadingOverview, setLoadingOverview] = useState(true);
  const [loadingLot, setLoadingLot] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [liveState, setLiveState] = useState<LiveConnectionState>("disconnected");
  const [geolocationState, setGeolocationState] = useState<GeolocationState>("idle");
  const [mapView, setMapView] = useState<MapViewState | null>(null);
  const [userPosition, setUserPosition] = useState<[number, number] | null>(null);
  const selectedLotIdRef = useRef<number | null>(null);
  const hasInitialLocationResolution = useRef(false);

  const numberFormatter = useMemo(
    () => new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }),
    [locale],
  );

  const fallbackCityLabel = language === "uk" ? "демо-місто" : "the demo city";

  const formatWholeNumber = useCallback(
    (value: number) => numberFormatter.format(value),
    [numberFormatter],
  );

  const formatDistance = useCallback(
    (value: number) => t("common.distanceCm", { value: formatWholeNumber(value) }),
    [formatWholeNumber, t],
  );

  const selectedLot = useMemo(
    () => overview?.lots.find((lot) => lot.id === selectedLotId) ?? null,
    [overview?.lots, selectedLotId],
  );

  const selectedSpot = useMemo(
    () => lotDetails?.spots.find((spot) => spot.id === selectedSpotId) ?? null,
    [lotDetails?.spots, selectedSpotId],
  );

  const applyOverview = useCallback((nextOverview: MapOverview) => {
    setOverview(nextOverview);
    setError(null);

    setSelectedLotId((previousLotId) => {
      if (nextOverview.lots.length === 0) {
        return null;
      }

      if (previousLotId && nextOverview.lots.some((lot) => lot.id === previousLotId)) {
        return previousLotId;
      }

      return nextOverview.lots[0].id;
    });

    setMapView((previousView) => {
      if (previousView) {
        return previousView;
      }

      return {
        center: [nextOverview.mapCenter.latitude, nextOverview.mapCenter.longitude],
        zoom: nextOverview.zoom,
      };
    });
  }, []);

  const applyLotDetails = useCallback((nextLot: LotDetails) => {
    setLotDetails(nextLot);
    setError(null);

    setSelectedSpotId((previousSpotId) => {
      if (nextLot.spots.length === 0) {
        return null;
      }

      if (previousSpotId && nextLot.spots.some((spot) => spot.id === previousSpotId)) {
        return previousSpotId;
      }

      return nextLot.spots[0].id;
    });
  }, []);

  const loadOverview = useCallback(async () => {
    setLoadingOverview(true);

    try {
      const nextOverview = await fetchMapOverview();
      applyOverview(nextOverview);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : t("monitoring.loadOverviewError"));
    } finally {
      setLoadingOverview(false);
    }
  }, [applyOverview, t]);

  const loadLotDetails = useCallback(
    async (lotId: number) => {
      setLoadingLot(true);

      try {
        const nextLot = (await fetchLotDetails(lotId)) as LotDetails;
        applyLotDetails(nextLot);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : t("monitoring.loadLotError"));
      } finally {
        setLoadingLot(false);
      }
    },
    [applyLotDetails, t],
  );

  const loadHistory = useCallback(async (spotId: number | null) => {
    if (!spotId) {
      setHistory(null);
      return;
    }

    setLoadingHistory(true);

    try {
      const nextHistory = await fetchSpotHistory(spotId, {
        maxPoints: 240,
      });
      setHistory(nextHistory);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : t("monitoring.loadHistoryError"));
    } finally {
      setLoadingHistory(false);
    }
  }, [t]);

  const locateUser = useCallback(
    (nextOverview: MapOverview) => {
      const fallbackView: MapViewState = {
        center: [nextOverview.mapCenter.latitude, nextOverview.mapCenter.longitude],
        zoom: nextOverview.zoom,
      };

      if (!("geolocation" in navigator)) {
        setGeolocationState("unsupported");
        setMapView(fallbackView);
        setUserPosition(null);
        return;
      }

      setGeolocationState("searching");

      navigator.geolocation.getCurrentPosition(
        (position) => {
          const nextPosition: [number, number] = [position.coords.latitude, position.coords.longitude];
          const nearestDistance = nextOverview.lots.length === 0
            ? Number.POSITIVE_INFINITY
            : Math.min(
                ...nextOverview.lots.map((lot) =>
                  haversineDistanceKm(nextPosition, [lot.latitude, lot.longitude]),
                ),
              );

          if (nearestDistance <= nextOverview.userLocationMaxDistanceKm) {
            setMapView({
              center: nextPosition,
              zoom: Math.max(nextOverview.zoom, 14),
            });
            setUserPosition(nextPosition);
            setGeolocationState("resolved");
            return;
          }

          setMapView(fallbackView);
          setUserPosition(null);
          setGeolocationState("fallback");
        },
        (geoError) => {
          setMapView(fallbackView);
          setUserPosition(null);
          setGeolocationState(geoError.code === geoError.PERMISSION_DENIED ? "denied" : "fallback");
        },
        {
          enableHighAccuracy: false,
          timeout: 5000,
          maximumAge: 60000,
        },
      );
    },
    [],
  );

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  useEffect(() => {
    if (!overview) {
      return;
    }

    if (hasInitialLocationResolution.current) {
      return;
    }

    hasInitialLocationResolution.current = true;
    locateUser(overview);
  }, [locateUser, overview]);

  useEffect(() => {
    if (!selectedLotId) {
      setLotDetails(null);
      setSelectedSpotId(null);
      return;
    }

    void loadLotDetails(selectedLotId);
  }, [loadLotDetails, selectedLotId]);

  useEffect(() => {
    void loadHistory(selectedSpotId);
  }, [loadHistory, selectedSpotId]);

  useEffect(() => {
    selectedLotIdRef.current = selectedLotId;
  }, [selectedLotId]);

  useEffect(() => {
    const connection = new HubConnectionBuilder()
      .withUrl(`${apiBaseUrl}/hubs/parking`, {
        accessTokenFactory: requestAccessToken,
      })
      .withAutomaticReconnect()
      .configureLogging(LogLevel.Warning)
      .build();

    connection.on("mapSnapshot", (snapshot: MapSnapshot) => {
      setOverview((previousOverview) => {
        if (!previousOverview) {
          return previousOverview;
        }

        return {
          ...previousOverview,
          summary: snapshot.summary,
          lots: snapshot.lots,
        };
      });

      setSelectedLotId((previousLotId) => {
        if (snapshot.lots.length === 0) {
          return null;
        }

        if (previousLotId && snapshot.lots.some((lot) => lot.id === previousLotId)) {
          return previousLotId;
        }

        return snapshot.lots[0].id;
      });

      setLoadingOverview(false);
      setError(null);

      if (selectedLotIdRef.current) {
        void loadLotDetails(selectedLotIdRef.current);
      }
    });

    connection.onreconnecting(() => {
      setLiveState("connecting");
    });

    connection.onreconnected(() => {
      setLiveState("connected");
    });

    connection.onclose(() => {
      setLiveState("disconnected");
    });

    setLiveState("connecting");

    void connection
      .start()
      .then(() => {
        setLiveState("connected");
      })
      .catch(() => {
        setLiveState("disconnected");
      });

    return () => {
      void connection.stop();
    };
  }, [loadLotDetails]);

  const refreshAll = useCallback(async () => {
    await loadOverview();

    if (selectedLotId) {
      await loadLotDetails(selectedLotId);
    }

    await loadHistory(selectedSpotId);
  }, [loadHistory, loadLotDetails, loadOverview, selectedLotId, selectedSpotId]);

  const locationHint = describeLocationMode(geolocationState, overview?.city ?? null, fallbackCityLabel, t);
  const occupancyPercent = overview
    ? new Intl.NumberFormat(locale, { style: "percent", maximumFractionDigits: 0 }).format(overview.summary.occupancyRate)
    : "-";
  const mapCenter: LatLngExpression = mapView?.center ?? [49.8419, 24.0315];

  return (
    <Container maxWidth={false} sx={{ px: { xs: 2, md: 4 }, py: 3.5 }}>
      <Stack spacing={3}>
        <Stack
          direction={{ xs: "column", lg: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "flex-start", lg: "center" }}
          spacing={2}
        >
          <Box>
            <Typography
              variant="overline"
              sx={{
                display: "block",
                color: "secondary.main",
                letterSpacing: "0.18em",
                fontWeight: 800,
              }}
            >
              {t("monitoring.overline")}
            </Typography>
            <Typography variant="h3" sx={{ maxWidth: 760, mb: 1 }}>
              {t("monitoring.title")}
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 720 }}>
              {t("monitoring.description")}
            </Typography>
          </Box>

          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25} alignItems={{ xs: "stretch", sm: "center" }}>
            <LiveStateChip state={liveState} />

            <Button
              variant="outlined"
              color="primary"
              startIcon={<LocationSearchingRoundedIcon />}
              onClick={() => {
                if (overview) {
                  locateUser(overview);
                }
              }}
              disabled={!overview}
            >
              {t("common.findMe")}
            </Button>

            <Button variant="contained" color="primary" startIcon={<RefreshRoundedIcon />} onClick={() => void refreshAll()}>
              {t("common.refresh")}
            </Button>
          </Stack>
        </Stack>

        {error ? <Alert severity="error">{error}</Alert> : null}

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              xl: "1.45fr 0.85fr",
            },
            gap: 3,
            alignItems: "stretch",
          }}
        >
          <Stack spacing={2.25}>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "repeat(2, minmax(0, 1fr))",
                  lg: "repeat(4, minmax(0, 1fr))",
                },
                gap: 1.5,
              }}
            >
              <SummaryCard
                title={t("monitoring.summary.lots")}
                value={overview ? formatWholeNumber(overview.summary.totalLots) : "-"}
                icon={<PlaceRoundedIcon />}
              />
              <SummaryCard
                title={t("monitoring.summary.freeSpots")}
                value={overview ? formatWholeNumber(overview.summary.freeSpots) : "-"}
                icon={<LocalParkingRoundedIcon />}
              />
              <SummaryCard
                title={t("monitoring.summary.occupiedNow")}
                value={overview ? formatWholeNumber(overview.summary.occupiedSpots) : "-"}
                icon={<TrafficRoundedIcon />}
              />
              <SummaryCard
                title={t("monitoring.summary.occupancy")}
                value={occupancyPercent}
                icon={<RouteRoundedIcon />}
              />
            </Box>

            <Paper
              elevation={0}
              sx={{
                px: 2,
                py: 1.35,
                borderRadius: "10px",
                display: "flex",
                alignItems: "center",
                gap: 1,
                maxWidth: "100%",
                bgcolor: "rgba(255,253,247,0.92)",
                border: "1px solid rgba(17, 97, 73, 0.10)",
              }}
            >
              <ExploreRoundedIcon color="primary" fontSize="small" />
              <Typography variant="body2" color="text.secondary">
                {locationHint}
              </Typography>
            </Paper>

            <Paper className="map-card" sx={{ borderRadius: "12px", border: "1px solid rgba(17, 97, 73, 0.12)" }}>
              {loadingOverview && !overview ? (
                <Stack justifyContent="center" alignItems="center" sx={{ minHeight: "100%" }} spacing={2}>
                  <CircularProgress size={32} />
                  <Typography variant="body2" color="text.secondary">
                    {t("monitoring.map.loading")}
                  </Typography>
                </Stack>
              ) : overview ? (
                <>
                  <MapContainer
                    center={mapCenter}
                    zoom={mapView?.zoom ?? 13}
                    scrollWheelZoom
                    zoomControl={false}
                    style={{ minHeight: "100%" }}
                  >
                    <MapViewUpdater
                      center={mapView?.center ?? [overview.mapCenter.latitude, overview.mapCenter.longitude]}
                      zoom={mapView?.zoom ?? overview.zoom}
                    />
                    <ZoomControl position="bottomright" />

                    <TileLayer
                      attribution="&copy; OpenStreetMap contributors"
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />

                    {userPosition ? (
                      <CircleMarker
                        center={userPosition}
                        radius={10}
                        pathOptions={{
                          color: "#0f172a",
                          weight: 3,
                          fillColor: "#38bdf8",
                          fillOpacity: 0.9,
                        }}
                      />
                    ) : null}

                    {overview.lots.map((lot) => {
                      const selected = lot.id === selectedLotId;
                      const color = occupancyColor(lot.occupancyRate);
                      const radius = selected ? 18 : 14 + Math.min(lot.totalSpots, 8);

                      return (
                        <CircleMarker
                          key={lot.id}
                          center={[lot.latitude, lot.longitude]}
                          radius={radius}
                          eventHandlers={{
                            click: () => setSelectedLotId(lot.id),
                          }}
                          pathOptions={{
                            color,
                            weight: selected ? 4 : 2,
                            fillColor: color,
                            fillOpacity: selected ? 0.32 : 0.22,
                          }}
                        />
                      );
                    })}
                  </MapContainer>

                  {overview.lots.length === 0 ? (
                    <Box className="map-empty-state">
                      <Paper
                        elevation={0}
                        sx={{
                          px: 3,
                          py: 2.5,
                          borderRadius: "10px",
                          maxWidth: 440,
                          textAlign: "center",
                          bgcolor: "rgba(255,253,247,0.94)",
                          border: "1px solid rgba(17, 97, 73, 0.10)",
                        }}
                      >
                        <LocalParkingRoundedIcon sx={{ fontSize: 40, color: "text.disabled", mb: 1 }} />
                        <Typography variant="h6" sx={{ mb: 0.5 }}>
                          {t("monitoring.map.emptyTitle")}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {t("monitoring.map.emptyDescription")}
                        </Typography>
                      </Paper>
                    </Box>
                  ) : null}
                </>
              ) : (
                <Stack justifyContent="center" alignItems="center" sx={{ minHeight: "100%" }} spacing={1}>
                  <LocalParkingRoundedIcon sx={{ fontSize: 44, color: "text.disabled" }} />
                  <Typography variant="h6">{t("monitoring.map.failedTitle")}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {t("monitoring.map.failedDescription")}
                  </Typography>
                </Stack>
              )}
            </Paper>
          </Stack>

          <Paper
            sx={{
              p: 2.5,
              borderRadius: "12px",
              border: "1px solid rgba(17, 97, 73, 0.12)",
              bgcolor: "rgba(255, 253, 247, 0.92)",
              minHeight: 560,
            }}
          >
            {selectedLot ? (
              <Stack spacing={2.5}>
                <Box>
                  <Typography variant="overline" sx={{ color: "secondary.main", fontWeight: 800, letterSpacing: "0.14em" }}>
                    {t("monitoring.selectedLot.overline")}
                  </Typography>
                  <Typography variant="h5" sx={{ mt: 0.5 }}>
                    {selectedLot.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {selectedLot.address}, {selectedLot.city}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {t("common.updatedAt")} {formatUpdateLabel(selectedLot.lastUpdatedAtUtc, locale, t)}
                  </Typography>
                </Box>

                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    gap: 1.25,
                  }}
                >
                  <SummaryCard
                    compact
                    title={t("common.totalSpots")}
                    value={formatWholeNumber(selectedLot.totalSpots)}
                    icon={<LocalParkingRoundedIcon />}
                  />
                  <SummaryCard
                    compact
                    title={t("common.freeSpots")}
                    value={formatWholeNumber(selectedLot.freeSpots)}
                    icon={<PlaceRoundedIcon />}
                  />
                  <SummaryCard
                    compact
                    title={t("common.occupiedSpots")}
                    value={formatWholeNumber(selectedLot.occupiedSpots)}
                    icon={<TrafficRoundedIcon />}
                  />
                  <SummaryCard
                    compact
                    title={t("common.lastUpdate")}
                    value={formatUpdateLabel(selectedLot.lastUpdatedAtUtc, locale, t)}
                    icon={<SensorsRoundedIcon />}
                    valueVariant="text"
                  />
                </Box>

                <Divider />

                <Stack spacing={1.5}>
                  <Typography variant="h6">{t("monitoring.spotsTitle")}</Typography>

                  {loadingLot && !lotDetails ? (
                    <Box sx={{ py: 3, textAlign: "center" }}>
                      <CircularProgress size={28} />
                    </Box>
                  ) : (
                    <Stack spacing={1.1}>
                      {lotDetails?.spots.map((spot) => {
                        const selected = spot.id === selectedSpotId;

                        return (
                          <Box
                            key={spot.id}
                            onClick={() => setSelectedSpotId(spot.id)}
                            sx={{
                              p: 1.5,
                              borderRadius: "10px",
                              border: "1px solid",
                              borderColor: selected ? "primary.main" : "divider",
                              bgcolor: selected ? "rgba(17,97,73,0.08)" : "rgba(255,255,255,0.72)",
                              cursor: "pointer",
                              transition: "all 160ms ease",
                              "&:hover": {
                                borderColor: "primary.main",
                                transform: "translateY(-1px)",
                              },
                            }}
                          >
                            <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1.5}>
                              <Box>
                                <Typography fontWeight={800}>{spot.displayName}</Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {spot.distanceCm !== null ? formatDistance(spot.distanceCm) : t("monitoring.firstMeasurementPending")}
                                </Typography>
                              </Box>

                              <Stack alignItems="flex-end" spacing={0.75}>
                                <SpotStatusChip occupied={spot.occupied} />
                                <Typography variant="caption" color="text.secondary">
                                  {formatUpdateLabel(spot.lastUpdatedAtUtc, locale, t)}
                                </Typography>
                              </Stack>
                            </Stack>
                          </Box>
                        );
                      })}
                    </Stack>
                  )}
                </Stack>

                <Divider />

                <Stack spacing={1.5}>
                  <Box>
                    <Typography variant="h6">{t("monitoring.historyTitle")}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {selectedSpot
                        ? t("monitoring.historyStatus", {
                            spot: selectedSpot.displayName,
                            status: selectedSpot.occupied ? t("monitoring.status.occupied") : t("monitoring.status.free"),
                          })
                        : t("monitoring.historySelectSpot")}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {selectedSpot ? formatDateTime(selectedSpot.lastUpdatedAtUtc, locale, t) : t("monitoring.historyAuto")}
                    </Typography>
                  </Box>

                  {loadingHistory ? (
                    <Box sx={{ py: 3, textAlign: "center" }}>
                      <CircularProgress size={26} />
                    </Box>
                  ) : (
                    <DistanceHistoryChart points={history?.points ?? []} />
                  )}
                </Stack>

                <Divider />

                <Stack spacing={1.25}>
                  <Typography variant="h6">{t("monitoring.recentChanges")}</Typography>

                  {lotDetails?.recentActivity.length ? (
                    <Stack spacing={1}>
                      {lotDetails.recentActivity.map((activity) => (
                        <Paper
                          key={`${activity.spotId}-${activity.measuredAtUtc}`}
                          elevation={0}
                          sx={{
                            p: 1.25,
                            borderRadius: "10px",
                            border: "1px solid",
                            borderColor: "divider",
                            bgcolor: "rgba(255,255,255,0.72)",
                          }}
                        >
                          <Stack direction="row" justifyContent="space-between" spacing={2}>
                            <Box>
                              <Typography fontWeight={700}>{activity.spotName}</Typography>
                              <Typography variant="caption" color="text.secondary">
                                {t("monitoring.distanceLabel", { value: formatWholeNumber(activity.distanceCm) })}
                              </Typography>
                            </Box>
                            <Box sx={{ textAlign: "right" }}>
                              <SpotStatusChip occupied={activity.occupied} />
                              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
                                {formatUpdateLabel(activity.measuredAtUtc, locale, t)}
                              </Typography>
                            </Box>
                          </Stack>
                        </Paper>
                      ))}
                    </Stack>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      {t("monitoring.recentChangesEmpty")}
                    </Typography>
                  )}
                </Stack>
              </Stack>
            ) : (
              <Stack justifyContent="center" alignItems="center" spacing={1.5} sx={{ minHeight: "100%" }}>
                <PlaceRoundedIcon sx={{ fontSize: 42, color: "text.disabled" }} />
                <Typography variant="h6">{t("monitoring.chooseParkingTitle")}</Typography>
                <Typography variant="body2" color="text.secondary" textAlign="center">
                  {t("monitoring.chooseParkingDescription")}
                </Typography>
              </Stack>
            )}
          </Paper>
        </Box>
      </Stack>
    </Container>
  );
}
