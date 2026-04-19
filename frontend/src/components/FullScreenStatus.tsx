import { Alert, Box, Button, CircularProgress, Paper, Stack, Typography } from "@mui/material";
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
          width: "min(100%, 560px)",
          p: { xs: 3, md: 4 },
          borderRadius: 6,
          border: "1px solid rgba(17, 97, 73, 0.10)",
          bgcolor: "rgba(255, 253, 247, 0.96)",
        }}
      >
        <Stack spacing={2.5} alignItems="flex-start">
          {loading ? <CircularProgress size={30} /> : null}

          <Box>
            <Typography variant="h4" sx={{ mb: 1 }}>
              {resolvedTitle}
            </Typography>
            <Typography color="text.secondary">{resolvedDescription}</Typography>
          </Box>

          <Alert severity={severity} sx={{ width: "100%" }}>
            {severity === "error"
              ? t("fullscreen.error")
              : t("fullscreen.info")}
          </Alert>

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
