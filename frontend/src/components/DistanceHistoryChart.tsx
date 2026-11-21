import { Box, Stack, Typography } from "@mui/material";
import { useI18n } from "../i18n/context";
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
  const { t } = useI18n();

  if (points.length === 0) {
    return (
      <Box
        sx={{
          border: "1px dashed",
          borderColor: "divider",
          borderRadius: "10px",
          p: 3,
          textAlign: "center",
          bgcolor: "rgba(255,255,255,0.72)",
        }}
      >
        <Typography variant="body2" color="text.secondary">
          {t("chart.empty")}
        </Typography>
      </Box>
    );
  }

  return (
    <Stack spacing={1.5}>
      <Box
        sx={{
          border: "1px solid",
          borderColor: "divider",
          borderRadius: "10px",
          p: 1,
          bgcolor: "rgba(255,255,255,0.74)",
          background:
            "linear-gradient(180deg, rgba(17,97,73,0.12) 0%, rgba(217,119,6,0.06) 100%)",
        }}
      >
        <svg width="100%" height="220" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={t("chart.aria")}>
          <polyline
            fill="none"
            stroke="#116149"
            strokeWidth="3"
            strokeLinejoin="round"
            strokeLinecap="round"
            points={normalizePoints(points)}
          />
        </svg>
      </Box>

      <Typography variant="caption" color="text.secondary">
        {t("chart.caption")}
      </Typography>
    </Stack>
  );
}
