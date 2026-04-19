import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import ErrorOutlineRoundedIcon from "@mui/icons-material/ErrorOutlineRounded";
import CheckCircleOutlineRoundedIcon from "@mui/icons-material/CheckCircleOutlineRounded";
import { Box, Button, CircularProgress, Paper, Stack, Typography } from "@mui/material";
import { useI18n } from "../i18n/LanguageProvider";

type FullScreenStatusProps = {
  title?: string;
  description?: string;
  titleKey?: string;
  descriptionKey?: string;
  actionLabel?: string;
  actionLabelKey?: string;
  onAction?: () => void;
  severity?: "info" | "warning" | "error" | "success";
  loading?: boolean;
};

export function FullScreenStatus({
  title,
  description,
  titleKey,
  descriptionKey,
  actionLabel,
  actionLabelKey,
  onAction,
  severity = "info",
  loading = false,
}: FullScreenStatusProps) {
  const { t } = useI18n();
  const resolvedTitle = titleKey ? t(titleKey) : title ?? "";
  const resolvedDescription = descriptionKey ? t(descriptionKey) : description ?? "";
  const resolvedActionLabel = actionLabelKey ? t(actionLabelKey) : actionLabel;
  const severityMeta = {
    info: {
      icon: <InfoOutlinedIcon fontSize="small" />,
      color: "#1d4ed8",
      background: "rgba(191, 219, 254, 0.35)",
      border: "rgba(59, 130, 246, 0.18)",
      message: t("fullscreen.info"),
    },
    warning: {
      icon: <WarningAmberRoundedIcon fontSize="small" />,
      color: "#b45309",
      background: "rgba(253, 230, 138, 0.30)",
      border: "rgba(217, 119, 6, 0.18)",
      message: t("fullscreen.info"),
    },
    error: {
      icon: <ErrorOutlineRoundedIcon fontSize="small" />,
      color: "#b91c1c",
      background: "rgba(254, 226, 226, 0.48)",
      border: "rgba(239, 68, 68, 0.18)",
      message: t("fullscreen.error"),
    },
    success: {
      icon: <CheckCircleOutlineRoundedIcon fontSize="small" />,
      color: "#166534",
      background: "rgba(220, 252, 231, 0.40)",
      border: "rgba(34, 197, 94, 0.18)",
      message: t("fullscreen.info"),
    },
  }[severity];

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        px: 2,
        py: 4,
      }}
    >
      <Paper
        elevation={0}
        sx={{
          width: "min(100%, 680px)",
          p: { xs: 3, md: 4.5 },
          borderRadius: "12px",
          border: "1px solid rgba(17, 97, 73, 0.10)",
          bgcolor: "rgba(255, 253, 247, 0.96)",
        }}
      >
        <Stack spacing={3}>
          <Stack direction="row" spacing={2} alignItems="flex-start">
            <Box
              sx={{
              width: 52,
              height: 52,
              display: "grid",
              placeItems: "center",
              borderRadius: "10px",
              bgcolor: "rgba(17, 97, 73, 0.08)",
              color: "primary.main",
              flexShrink: 0,
              }}
            >
              {loading ? <CircularProgress size={24} /> : severityMeta.icon}
            </Box>

            <Box sx={{ minWidth: 0 }}>
              <Typography variant="h4" sx={{ mb: 1 }}>
                {resolvedTitle}
              </Typography>
              <Typography color="text.secondary">{resolvedDescription}</Typography>
            </Box>
          </Stack>

          <Box
            sx={{
              width: "100%",
              p: 1.75,
              borderRadius: "10px",
              border: "1px solid",
              borderColor: severityMeta.border,
              bgcolor: severityMeta.background,
              color: severityMeta.color,
            }}
          >
            <Stack direction="row" spacing={1.25} alignItems="flex-start">
              <Box sx={{ mt: "2px", display: "grid", placeItems: "center" }}>
                {severityMeta.icon}
              </Box>
              <Typography variant="body2" sx={{ lineHeight: 1.6 }}>
                {severityMeta.message}
              </Typography>
            </Stack>
          </Box>

          {resolvedActionLabel && onAction ? (
            <Button variant="contained" onClick={onAction}>
              {resolvedActionLabel}
            </Button>
          ) : null}
        </Stack>
      </Paper>
    </Box>
  );
}
