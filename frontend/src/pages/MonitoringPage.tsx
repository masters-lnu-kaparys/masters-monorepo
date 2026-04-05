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
  Chip,
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
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap, ZoomControl } from "react-leaflet";
import { apiBaseUrl, requestAccessToken } from "../api/http";
import { fetchLotDetails, fetchMapOverview, fetchSpotHistory } from "../api/client";
import { DistanceHistoryChart } from "../components/DistanceHistoryChart";
import type { LotDetails, MapOverview, MapSnapshot, SpotHistory } from "../types/api";

type LiveConnectionState = "connecting" | "connected" | "disconnected";
type GeolocationState = "idle" | "searching" | "resolved" | "fallback" | "denied" | "unsupported";
type MapViewState = {
  center: [number, number];
  zoom: number;
};

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
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        minHeight: 118,
        borderRadius: 4,
        border: "1px solid rgba(17, 97, 73, 0.10)",
        bgcolor: "rgba(255, 253, 247, 0.92)",
        backdropFilter: "blur(12px)",
      }}
    >
      <Stack direction="row" spacing={1.5} alignItems="flex-start">
        <Box
          sx={{
            width: 46,
            height: 46,
            borderRadius: 3,
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
              lineHeight: 1.1,
              letterSpacing: "0.08em",
            }}
          >
            {title}
          </Typography>
          <Typography variant="h4" fontWeight={800} sx={{ lineHeight: 1.1, mt: 1 }}>
            {value}
          </Typography>
        </Box>
      </Stack>
    </Paper>
  );
}

function LiveStateChip({ state }: { state: LiveConnectionState }) {
  if (state === "connected") {
    return <Chip color="success" icon={<SensorsRoundedIcon />} label="Оновлюється наживо" />;
  }

  if (state === "connecting") {
    return <Chip color="warning" icon={<SensorsRoundedIcon />} label="Підключаємо оновлення" />;
  }

  return <Chip color="default" icon={<SensorsRoundedIcon />} label="Працюємо з останніми даними" />;
}

function SpotStatusChip({ occupied }: { occupied: boolean }) {
  return (
    <Chip
      size="small"
      color={occupied ? "warning" : "success"}
      label={occupied ? "Зайнято" : "Вільно"}
      sx={{ minWidth: 88 }}
    />
  );
}

function formatUpdateLabel(utc: string | null): string {
  if (!utc) {
    return "ще немає даних";
  }

  const now = Date.now();
  const measuredAt = new Date(utc).getTime();
  const diffMinutes = Math.round((now - measuredAt) / 60000);

  if (diffMinutes <= 1) {
    return "щойно";
  }

  if (diffMinutes < 60) {
    return `${diffMinutes} хв тому`;
  }

  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) {
    return `${diffHours} год тому`;
  }

  return new Date(utc).toLocaleString();
}

function formatDateTime(utc: string | null): string {
  if (!utc) {
    return "немає оновлень";
  }

  return new Date(utc).toLocaleString();
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

function describeLocationMode(state: GeolocationState, city: string | null) {
  switch (state) {
    case "resolved":
      return "Карта центрована до вашої локації.";
    case "denied":
      return `Доступ до геолокації вимкнено. Показуємо демо-місто ${city ?? "на карті"}.`;
    case "unsupported":
      return `Браузер не підтримує геолокацію. Показуємо демо-місто ${city ?? "на карті"}.`;
    case "fallback":
      return `Поруч не знайдено доступних парковок. Показуємо демо-місто ${city ?? "на карті"}.`;
    case "searching":
      return "Шукаємо найближчі парковки відносно вашої локації.";
    default:
      return `Показуємо парковки міста ${city ?? "за замовчуванням"}.`;
  }
}

export function MonitoringPage() {
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
      setError(loadError instanceof Error ? loadError.message : "Не вдалося завантажити карту парковок.");
    } finally {
      setLoadingOverview(false);
    }
  }, [applyOverview]);

  const loadLotDetails = useCallback(
    async (lotId: number) => {
      setLoadingLot(true);

      try {
        const nextLot = (await fetchLotDetails(lotId)) as LotDetails;
        applyLotDetails(nextLot);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Не вдалося завантажити дані парковки.");
      } finally {
        setLoadingLot(false);
      }
    },
    [applyLotDetails],
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
      setError(loadError instanceof Error ? loadError.message : "Не вдалося завантажити історію місця.");
    } finally {
      setLoadingHistory(false);
    }
  }, []);

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

  const locationHint = describeLocationMode(geolocationState, overview?.city ?? null);
  const occupancyPercent = overview ? `${(overview.summary.occupancyRate * 100).toFixed(0)}%` : "-";
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
              SMART PARKING MONITORING
            </Typography>
            <Typography variant="h3" sx={{ maxWidth: 760, mb: 1 }}>
              Парковки поруч у реальному часі
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 720 }}>
              На карті видно завантаженість міських парковок, а в панелі праворуч можна роздивитися кожне місце окремо.
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
              Знайти мене
            </Button>

            <Button variant="contained" color="primary" startIcon={<RefreshRoundedIcon />} onClick={() => void refreshAll()}>
              Оновити
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
                title="Парковки"
                value={overview ? String(overview.summary.totalLots) : "-"}
                icon={<PlaceRoundedIcon />}
              />
              <SummaryCard
                title="Вільні місця"
                value={overview ? String(overview.summary.freeSpots) : "-"}
                icon={<LocalParkingRoundedIcon />}
              />
              <SummaryCard
                title="Зайнято зараз"
                value={overview ? String(overview.summary.occupiedSpots) : "-"}
                icon={<TrafficRoundedIcon />}
              />
              <SummaryCard
                title="Заповненість"
                value={occupancyPercent}
                icon={<RouteRoundedIcon />}
              />
            </Box>

            <Paper
              elevation={0}
              sx={{
                px: 2,
                py: 1.35,
                borderRadius: 4,
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

            <Paper className="map-card" sx={{ borderRadius: 6, border: "1px solid rgba(17, 97, 73, 0.12)" }}>
              {loadingOverview && !overview ? (
                <Stack justifyContent="center" alignItems="center" sx={{ minHeight: "100%" }} spacing={2}>
                  <CircularProgress size={32} />
                  <Typography variant="body2" color="text.secondary">
                    Завантажуємо карту парковок...
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
                      >
                        <Tooltip direction="top" opacity={1} className="map-tooltip">
                          <div>
                            <h4>Ви тут</h4>
                            <p>Карта показує найближчі доступні парковки.</p>
                          </div>
                        </Tooltip>
                      </CircleMarker>
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
                        >
                          <Tooltip direction="top" opacity={1} className="map-tooltip" permanent={selected}>
                            <div>
                              <h4>{lot.name}</h4>
                              <p>
                                {lot.freeSpots} вільно з {lot.totalSpots} місць
                              </p>
                            </div>
                          </Tooltip>
                        </CircleMarker>
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
                          borderRadius: 4,
                          maxWidth: 440,
                          textAlign: "center",
                          bgcolor: "rgba(255,253,247,0.94)",
                          border: "1px solid rgba(17, 97, 73, 0.10)",
                        }}
                      >
                        <LocalParkingRoundedIcon sx={{ fontSize: 40, color: "text.disabled", mb: 1 }} />
                        <Typography variant="h6" sx={{ mb: 0.5 }}>
                          Наразі немає доступних парковок
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Щойно адміністратор додасть локації або воркер отримає нові дані, маркери з&apos;являться тут автоматично.
                        </Typography>
                      </Paper>
                    </Box>
                  ) : null}
                </>
              ) : (
                <Stack justifyContent="center" alignItems="center" sx={{ minHeight: "100%" }} spacing={1}>
                  <LocalParkingRoundedIcon sx={{ fontSize: 44, color: "text.disabled" }} />
                  <Typography variant="h6">Не вдалося підготувати карту</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Спробуй оновити сторінку або перевірити запуск backend API.
                  </Typography>
                </Stack>
              )}
            </Paper>
          </Stack>

          <Paper
            sx={{
              p: 2.5,
              borderRadius: 6,
              border: "1px solid rgba(17, 97, 73, 0.12)",
              bgcolor: "rgba(255, 253, 247, 0.92)",
              minHeight: 560,
            }}
          >
            {selectedLot ? (
              <Stack spacing={2.5}>
                <Box>
                  <Typography variant="overline" sx={{ color: "secondary.main", fontWeight: 800, letterSpacing: "0.14em" }}>
                    ОБРАНА ПАРКОВКА
                  </Typography>
                  <Typography variant="h5" sx={{ mt: 0.5 }}>
                    {selectedLot.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {selectedLot.address}, {selectedLot.city}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Оновлено {formatUpdateLabel(selectedLot.lastUpdatedAtUtc)}
                  </Typography>
                </Box>

                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(4, minmax(0, 1fr))" },
                    gap: 1.25,
                  }}
                >
                  <SummaryCard title="Всього місць" value={String(selectedLot.totalSpots)} icon={<LocalParkingRoundedIcon />} />
                  <SummaryCard title="Вільно" value={String(selectedLot.freeSpots)} icon={<PlaceRoundedIcon />} />
                  <SummaryCard title="Зайнято" value={String(selectedLot.occupiedSpots)} icon={<TrafficRoundedIcon />} />
                  <SummaryCard
                    title="Останнє оновлення"
                    value={formatUpdateLabel(selectedLot.lastUpdatedAtUtc)}
                    icon={<SensorsRoundedIcon />}
                  />
                </Box>

                <Divider />

                <Stack spacing={1.5}>
                  <Typography variant="h6">Місця на парковці</Typography>

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
                              borderRadius: 3,
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
                                  {spot.distanceCm ? `${spot.distanceCm.toFixed(0)} см` : "очікуємо перше вимірювання"}
                                </Typography>
                              </Box>

                              <Stack alignItems="flex-end" spacing={0.75}>
                                <SpotStatusChip occupied={spot.occupied} />
                                <Typography variant="caption" color="text.secondary">
                                  {formatUpdateLabel(spot.lastUpdatedAtUtc)}
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
                    <Typography variant="h6">Динаміка вибраного місця</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {selectedSpot
                        ? `${selectedSpot.displayName} — ${selectedSpot.occupied ? "зайнято" : "вільно"}`
                        : "Оберіть місце на парковці"}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {selectedSpot ? formatDateTime(selectedSpot.lastUpdatedAtUtc) : "Історія підвантажиться автоматично"}
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
                  <Typography variant="h6">Останні зміни</Typography>

                  {lotDetails?.recentActivity.length ? (
                    <Stack spacing={1}>
                      {lotDetails.recentActivity.map((activity) => (
                        <Paper
                          key={`${activity.spotId}-${activity.measuredAtUtc}`}
                          elevation={0}
                          sx={{
                            p: 1.25,
                            borderRadius: 3,
                            border: "1px solid",
                            borderColor: "divider",
                            bgcolor: "rgba(255,255,255,0.72)",
                          }}
                        >
                          <Stack direction="row" justifyContent="space-between" spacing={2}>
                            <Box>
                              <Typography fontWeight={700}>{activity.spotName}</Typography>
                              <Typography variant="caption" color="text.secondary">
                                Відстань: {activity.distanceCm.toFixed(0)} см
                              </Typography>
                            </Box>
                            <Box sx={{ textAlign: "right" }}>
                              <SpotStatusChip occupied={activity.occupied} />
                              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
                                {formatUpdateLabel(activity.measuredAtUtc)}
                              </Typography>
                            </Box>
                          </Stack>
                        </Paper>
                      ))}
                    </Stack>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      Щойно з&apos;являться нові події, вони відобразяться тут.
                    </Typography>
                  )}
                </Stack>
              </Stack>
            ) : (
              <Stack justifyContent="center" alignItems="center" spacing={1.5} sx={{ minHeight: "100%" }}>
                <PlaceRoundedIcon sx={{ fontSize: 42, color: "text.disabled" }} />
                <Typography variant="h6">Оберіть парковку на карті</Typography>
                <Typography variant="body2" color="text.secondary" textAlign="center">
                  Праворуч з&apos;явиться детальна інформація про місця, доступність і недавні оновлення.
                </Typography>
              </Stack>
            )}
          </Paper>
        </Box>
      </Stack>
    </Container>
  );
}
