import BlockRoundedIcon from "@mui/icons-material/BlockRounded";
import { Box, Button, Paper, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { APP_ROUTES } from "../app/routes";
import { useI18n } from "../i18n/context";

export function ForbiddenPage() {
  const { t } = useI18n();

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
          borderRadius: "12px",
          border: "1px solid rgba(17, 97, 73, 0.10)",
          bgcolor: "rgba(255, 253, 247, 0.96)",
        }}
      >
        <Stack spacing={2.5}>
          <Box
            sx={{
              width: 52,
              height: 52,
              display: "grid",
              placeItems: "center",
              borderRadius: "10px",
              bgcolor: "rgba(211, 47, 47, 0.08)",
              color: "error.main",
            }}
          >
            <BlockRoundedIcon sx={{ fontSize: 30 }} />
          </Box>
          <Typography variant="h4">{t("auth.forbidden.title")}</Typography>
          <Typography color="text.secondary">
            {t("auth.forbidden.description")}
          </Typography>

          <Box
            sx={{
              p: 2,
              borderRadius: "10px",
              border: "1px solid rgba(217, 119, 6, 0.18)",
              bgcolor: "rgba(217, 119, 6, 0.08)",
            }}
          >
            <Typography color="text.secondary">{t("auth.forbidden.alert")}</Typography>
          </Box>

          <Box>
            <Button component={RouterLink} to={APP_ROUTES.home} variant="contained">
              {t("auth.forbidden.backToMap")}
            </Button>
          </Box>
        </Stack>
      </Paper>
    </Box>
  );
}
