import BlockRoundedIcon from "@mui/icons-material/BlockRounded";
import { Alert, Box, Button, Paper, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { useI18n } from "../i18n/LanguageProvider";

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
          borderRadius: 6,
          border: "1px solid rgba(17, 97, 73, 0.10)",
          bgcolor: "rgba(255, 253, 247, 0.96)",
          textAlign: "center",
        }}
      >
        <Stack spacing={2.25} alignItems="center">
          <BlockRoundedIcon sx={{ fontSize: 52, color: "error.main" }} />
          <Typography variant="h4">{t("auth.forbidden.title")}</Typography>
          <Typography color="text.secondary">
            {t("auth.forbidden.description")}
          </Typography>
          <Alert severity="warning" sx={{ width: "100%", textAlign: "left" }}>
            {t("auth.forbidden.alert")}
          </Alert>
          <Button component={RouterLink} to="/" variant="contained">
            {t("auth.forbidden.backToMap")}
          </Button>
        </Stack>
      </Paper>
    </Box>
  );
}
