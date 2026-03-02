import AccessTimeRoundedIcon from "@mui/icons-material/AccessTimeRounded";
import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
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
import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { fetchDashboardSummary, fetchSpotHistory, fetchSpots } from "./api/client";
import { DistanceHistoryChart } from "./components/DistanceHistoryChart";
import type { DashboardSummary, SpotHistory, SpotState } from "./types/api";

const DASHBOARD_REFRESH_MS = 5000;

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

export default function App() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [spots, setSpots] = useState<SpotState[]>([]);
  const [selectedSpotId, setSelectedSpotId] = useState<number | null>(null);
  const [history, setHistory] = useState<SpotHistory | null>(null);
  const [loadingDashboard, setLoadingDashboard] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedSpot = useMemo(
    () => spots.find((spot) => spot.id === selectedSpotId) ?? null,
    [spots, selectedSpotId],
  );

  const loadDashboard = useCallback(async () => {
    setLoadingDashboard(true);

    try {
      const [nextSummary, nextSpots] = await Promise.all([fetchDashboardSummary(), fetchSpots()]);
      setSummary(nextSummary);
      setSpots(nextSpots);

      if (nextSpots.length === 0) {
        setSelectedSpotId(null);
        setHistory(null);
      } else if (!nextSpots.some((spot) => spot.id === selectedSpotId)) {
        setSelectedSpotId(nextSpots[0].id);
      }

      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load dashboard data.");
    } finally {
      setLoadingDashboard(false);
    }
  }, [selectedSpotId]);

  const loadHistory = useCallback(async () => {
    if (!selectedSpotId) {
      setHistory(null);
      return;
    }

    setLoadingHistory(true);

    try {
      const historyResponse = await fetchSpotHistory(selectedSpotId, { maxPoints: 1000 });
      setHistory(historyResponse);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load history.");
    } finally {
      setLoadingHistory(false);
    }
  }, [selectedSpotId]);

  useEffect(() => {
    void loadDashboard();

    const intervalId = window.setInterval(() => {
      void loadDashboard();
    }, DASHBOARD_REFRESH_MS);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [loadDashboard]);

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
                  Click a row to inspect distance history.
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
