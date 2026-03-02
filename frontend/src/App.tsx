import AccessTimeRoundedIcon from "@mui/icons-material/AccessTimeRounded";
import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import CloudDoneRoundedIcon from "@mui/icons-material/CloudDoneRounded";
import CloudOffRoundedIcon from "@mui/icons-material/CloudOffRounded";
import CloudSyncRoundedIcon from "@mui/icons-material/CloudSyncRounded";
import EventSeatRoundedIcon from "@mui/icons-material/EventSeatRounded";
import LocalParkingRoundedIcon from "@mui/icons-material/LocalParkingRounded";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import {
  Alert,
  AppBar,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Toolbar,
  Typography,
} from "@mui/material";
import { HubConnectionBuilder, LogLevel } from "@microsoft/signalr";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { apiBaseUrl, fetchDashboardSummary, fetchSpotHistory, fetchSpots } from "./api/client";
import { DistanceHistoryChart } from "./components/DistanceHistoryChart";
import type { DashboardSnapshot, DashboardSummary, SpotHistory, SpotState } from "./types/api";

type LiveConnectionState = "connecting" | "connected" | "disconnected";

function formatUtc(utc: string | null): string {
  if (!utc) {
    return "-";
  }

  return new Date(utc).toLocaleString();
}

function SummaryCard({
  title,
  value,
  icon,
}: {
  title: string;
  value: string;
  icon: ReactNode;
}) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        borderRadius: 3,
        border: "1px solid",
        borderColor: "divider",
        background: "linear-gradient(170deg, #ffffff 0%, #f0f9ff 100%)",
      }}
    >
      <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2}>
        <Box>
          <Typography variant="body2" color="text.secondary">
            {title}
          </Typography>
          <Typography variant="h5" fontWeight={700}>
            {value}
          </Typography>
        </Box>
        <Box sx={{ color: "primary.main", display: "flex", alignItems: "center" }}>{icon}</Box>
      </Stack>
    </Paper>
  );
}

function LiveStateChip({ state }: { state: LiveConnectionState }) {
  if (state === "connected") {
    return <Chip color="success" icon={<CloudDoneRoundedIcon />} label="Live connected" />;
  }

  if (state === "connecting") {
    return <Chip color="warning" icon={<CloudSyncRoundedIcon />} label="Live reconnecting" />;
  }

  return <Chip color="default" icon={<CloudOffRoundedIcon />} label="Live offline" />;
}

export default function App() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [spots, setSpots] = useState<SpotState[]>([]);
  const [selectedSpotId, setSelectedSpotId] = useState<number | null>(null);
  const [history, setHistory] = useState<SpotHistory | null>(null);
  const [loadingDashboard, setLoadingDashboard] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [liveState, setLiveState] = useState<LiveConnectionState>("disconnected");

  const selectedSpot = useMemo(
    () => spots.find((spot) => spot.id === selectedSpotId) ?? null,
    [spots, selectedSpotId],
  );

  const applySpotList = useCallback((nextSpots: SpotState[]) => {
    setSpots(nextSpots);

    setSelectedSpotId((previousSpotId) => {
      if (nextSpots.length === 0) {
        return null;
      }

      if (previousSpotId && nextSpots.some((spot) => spot.id === previousSpotId)) {
        return previousSpotId;
      }

      return nextSpots[0].id;
    });
  }, []);

  const loadDashboard = useCallback(async () => {
    setLoadingDashboard(true);

    try {
      const [nextSummary, nextSpots] = await Promise.all([fetchDashboardSummary(), fetchSpots()]);
      setSummary(nextSummary);
      applySpotList(nextSpots);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load dashboard data.");
    } finally {
      setLoadingDashboard(false);
    }
  }, [applySpotList]);

  const loadHistory = useCallback(async () => {
    if (!selectedSpotId) {
      setHistory(null);
      return;
    }

    setLoadingHistory(true);

    try {
      const historyResponse = await fetchSpotHistory(selectedSpotId, { maxPoints: 1000 });
      setHistory(historyResponse);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load history.");
    } finally {
      setLoadingHistory(false);
    }
  }, [selectedSpotId]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    const connection = new HubConnectionBuilder()
      .withUrl(`${apiBaseUrl}/hubs/parking`)
      .withAutomaticReconnect()
      .configureLogging(LogLevel.Warning)
      .build();

    connection.on("dashboardSnapshot", (snapshot: DashboardSnapshot) => {
      setSummary(snapshot.summary);
      applySpotList(snapshot.spots);
      setLoadingDashboard(false);
      setError(null);
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
  }, [applySpotList]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const occupancyPercent = summary ? `${(summary.occupancyRate * 100).toFixed(1)}%` : "-";

  return (
    <>
      <AppBar position="sticky" color="inherit" elevation={0} sx={{ borderBottom: "1px solid", borderColor: "divider" }}>
        <Toolbar>
          <LocalParkingRoundedIcon color="primary" sx={{ mr: 1.5 }} />
          <Typography variant="h6" fontWeight={700} sx={{ flexGrow: 1 }}>
            Parking Monitoring Dashboard
          </Typography>

          <Stack direction="row" spacing={1.5} alignItems="center">
            <LiveStateChip state={liveState} />
            <Button
              variant="contained"
              color="primary"
              startIcon={<RefreshRoundedIcon />}
              onClick={() => {
                void loadDashboard();
                void loadHistory();
              }}
            >
              Refresh
            </Button>
          </Stack>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Stack spacing={3}>
          {error ? <Alert severity="error">{error}</Alert> : null}

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                sm: "repeat(2, minmax(0, 1fr))",
                lg: "repeat(4, minmax(0, 1fr))",
              },
              gap: 2,
            }}
          >
            <SummaryCard title="Total spots" value={summary ? String(summary.totalSpots) : "-"} icon={<EventSeatRoundedIcon />} />
            <SummaryCard title="Occupied spots" value={summary ? String(summary.occupiedSpots) : "-"} icon={<CheckCircleRoundedIcon />} />
            <SummaryCard title="Occupancy" value={occupancyPercent} icon={<LocalParkingRoundedIcon />} />
            <SummaryCard
              title="Last telemetry"
              value={summary ? formatUtc(summary.lastTelemetryAtUtc) : "-"}
              icon={<AccessTimeRoundedIcon />}
            />
          </Box>

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                lg: "1.25fr 1fr",
              },
              gap: 2,
            }}
          >
            <Paper elevation={0} sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider", overflow: "hidden" }}>
              <Box sx={{ p: 2, borderBottom: "1px solid", borderColor: "divider" }}>
                <Typography variant="h6" fontWeight={700}>
                  Parking Spots
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Live updates are pushed via SignalR. Click a row to inspect history.
                </Typography>
              </Box>

              {loadingDashboard ? (
                <Box sx={{ p: 3, textAlign: "center" }}>
                  <CircularProgress size={28} />
                </Box>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Device</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell align="right">Distance (cm)</TableCell>
                      <TableCell align="right">Last update</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {spots.map((spot) => (
                      <TableRow
                        key={spot.id}
                        hover
                        selected={spot.id === selectedSpotId}
                        onClick={() => setSelectedSpotId(spot.id)}
                        sx={{ cursor: "pointer" }}
                      >
                        <TableCell>{spot.displayName}</TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            color={spot.occupied ? "error" : "success"}
                            label={spot.occupied ? "Occupied" : "Free"}
                          />
                        </TableCell>
                        <TableCell align="right">{spot.distanceCm?.toFixed(1) ?? "-"}</TableCell>
                        <TableCell align="right">{formatUtc(spot.lastTelemetryAtUtc)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </Paper>

            <Paper elevation={0} sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider", p: 2 }}>
              <Stack spacing={2}>
                <Box>
                  <Typography variant="h6" fontWeight={700}>
                    Spot History
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {selectedSpot ? `Device: ${selectedSpot.deviceId}` : "Select a spot"}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    History updates on demand via the Refresh button.
                  </Typography>
                </Box>

                {loadingHistory ? (
                  <Box sx={{ textAlign: "center", py: 3 }}>
                    <CircularProgress size={26} />
                  </Box>
                ) : (
                  <>
                    <DistanceHistoryChart points={history?.points ?? []} />
                    <Typography variant="caption" color="text.secondary">
                      Points: {history?.points.length ?? 0}
                    </Typography>
                  </>
                )}
              </Stack>
            </Paper>
          </Box>
        </Stack>
      </Container>
    </>
  );
}
