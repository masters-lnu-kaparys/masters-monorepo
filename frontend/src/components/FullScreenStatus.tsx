import { Alert, Box, Button, CircularProgress, Paper, Stack, Typography } from "@mui/material";

type FullScreenStatusProps = {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  severity?: "info" | "warning" | "error" | "success";
  loading?: boolean;
};

export function FullScreenStatus({
  title,
  description,
  actionLabel,
  onAction,
  severity = "info",
  loading = false,
}: FullScreenStatusProps) {
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
              {title}
            </Typography>
            <Typography color="text.secondary">{description}</Typography>
          </Box>

          <Alert severity={severity} sx={{ width: "100%" }}>
            {severity === "error"
              ? "Перевір конфігурацію або права доступу і спробуй ще раз."
              : "Стан застосунку контролюється і не вимагає ручних обхідних дій."}
          </Alert>

          {actionLabel && onAction ? (
            <Button variant="contained" onClick={onAction}>
              {actionLabel}
            </Button>
          ) : null}
        </Stack>
      </Paper>
    </Box>
  );
}
