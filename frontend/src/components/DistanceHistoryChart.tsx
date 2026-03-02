import { Box, Typography } from "@mui/material";
import type { SpotHistoryPoint } from "../types/api";

type DistanceHistoryChartProps = {
  points: SpotHistoryPoint[];
};

const WIDTH = 720;
const HEIGHT = 220;
const PADDING = 24;

function normalizePoints(points: SpotHistoryPoint[]) {
  if (points.length === 0) {
    return "";
  }

  const distances = points.map((point) => point.distanceCm);
  const minDistance = Math.min(...distances);
  const maxDistance = Math.max(...distances);
  const distanceSpan = maxDistance - minDistance || 1;
  const stepX = points.length <= 1 ? 0 : (WIDTH - PADDING * 2) / (points.length - 1);

  return points
    .map((point, index) => {
      const x = PADDING + index * stepX;
      const yRatio = (point.distanceCm - minDistance) / distanceSpan;
      const y = HEIGHT - PADDING - yRatio * (HEIGHT - PADDING * 2);
      return `${x},${y}`;
    })
    .join(" ");
}

export function DistanceHistoryChart({ points }: DistanceHistoryChartProps) {
  if (points.length === 0) {
    return (
      <Box
        sx={{
          border: "1px dashed",
          borderColor: "divider",
          borderRadius: 2,
          p: 3,
          textAlign: "center",
        }}
      >
        <Typography variant="body2" color="text.secondary">
          No telemetry points in selected range.
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 2,
        p: 1,
        background:
          "linear-gradient(180deg, rgba(12,74,110,0.06) 0%, rgba(2,132,199,0.02) 100%)",
      }}
    >
      <svg width="100%" height="220" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Distance history chart">
        <polyline
          fill="none"
          stroke="#0284c7"
          strokeWidth="3"
          strokeLinejoin="round"
          strokeLinecap="round"
          points={normalizePoints(points)}
        />
      </svg>
    </Box>
  );
}
