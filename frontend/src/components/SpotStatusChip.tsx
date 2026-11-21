import { Chip } from "@mui/material";
import { useI18n } from "../i18n/context";
import type { SpotDataStatus } from "../types/api";

export function SpotStatusChip({ occupied, dataStatus = "missing" }: { occupied: boolean; dataStatus?: SpotDataStatus }) {
  const { t } = useI18n();
  const key = dataStatus === "missing" ? "monitoring.status.missing"
    : dataStatus === "stale" ? "monitoring.status.stale"
    : occupied ? "monitoring.status.occupied" : "monitoring.status.free";
  return <Chip size="small" label={t(key)} color={dataStatus !== "current" ? "default" : occupied ? "warning" : "success"} />;
}
