import { useAuth0 } from "@auth0/auth0-react";
import BoltRoundedIcon from "@mui/icons-material/BoltRounded";
import EastRoundedIcon from "@mui/icons-material/EastRounded";
import InsightsRoundedIcon from "@mui/icons-material/InsightsRounded";
import LocalParkingRoundedIcon from "@mui/icons-material/LocalParkingRounded";
import { Box, Button, Container, Paper, Stack, Typography } from "@mui/material";
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { APP_ROUTES } from "../app/routes";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { useI18n } from "../i18n/context";

type HighlightRowProps = {
  icon: ReactNode;
  title: string;
  description: string;
};

function HighlightRow({ icon, title, description }: HighlightRowProps) {
  return (
    <Stack direction="row" spacing={1.75} alignItems="flex-start">
      <Box
        sx={{
          width: 44,
          height: 44,
          display: "grid",
          placeItems: "center",
          borderRadius: "10px",
          bgcolor: "rgba(17, 97, 73, 0.08)",
          color: "primary.main",
          flexShrink: 0,
        }}
      >
        {icon}
      </Box>

      <Box>
        <Typography sx={{ fontWeight: 800, mb: 0.5 }}>{title}</Typography>
        <Typography color="text.secondary">{description}</Typography>
      </Box>
    </Stack>
  );
}

export function LoginPage() {
  const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0();
  const { t } = useI18n();
  const location = useLocation();
  const returnTo = typeof location.state?.returnTo === "string" ? location.state.returnTo : APP_ROUTES.home;

  if (!isLoading && isAuthenticated) {
    return <Navigate to={returnTo} replace />;
  }

  return (
    <Box
      sx={{
        minHeight: "100vh",
        py: { xs: 3, md: 5 },
        background: `
          radial-gradient(circle at top left, rgba(217, 119, 6, 0.10), transparent 24%),
          radial-gradient(circle at top right, rgba(17, 97, 73, 0.12), transparent 26%),
          linear-gradient(180deg, #f6f1e4 0%, #fcfaf4 100%)
        `,
      }}
    >
      <Container maxWidth="xl">
        <Stack direction="row" justifyContent="flex-end" sx={{ mb: 2 }}>
          <LanguageSwitcher />
        </Stack>

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", xl: "minmax(0, 1.15fr) minmax(360px, 0.85fr)" },
            gap: 3,
            alignItems: "start",
          }}
        >
          <Paper
            elevation={0}
            sx={{
              p: { xs: 3, md: 5 },
              borderRadius: "12px",
              border: "1px solid rgba(17, 97, 73, 0.10)",
              bgcolor: "rgba(255, 252, 245, 0.82)",
              backdropFilter: "blur(14px)",
            }}
          >
            <Stack spacing={4}>
              <Box
                sx={{
                  display: "inline-flex",
                  width: "fit-content",
                  px: 1.75,
                  py: 0.9,
                  borderRadius: "8px",
                  bgcolor: "secondary.main",
                  color: "secondary.contrastText",
                }}
              >
                <Typography variant="overline" sx={{ fontWeight: 800, letterSpacing: "0.16em" }}>
                  {t("auth.login.badge.platform")}
                </Typography>
              </Box>

              <Box sx={{ maxWidth: 780 }}>
                <Typography
                  variant="h1"
                  sx={{
                    fontSize: { xs: "2.85rem", md: "4.5rem" },
                    lineHeight: { xs: 1.02, md: 0.97 },
                    mb: 2,
                  }}
                >
                  {t("auth.login.heroTitle")}
                </Typography>
                <Typography
                  sx={{
                    maxWidth: 700,
                    fontSize: { xs: "1rem", md: "1.12rem" },
                    color: "text.secondary",
                  }}
                >
                  {t("auth.login.heroDescription")}
                </Typography>
              </Box>

              <Stack spacing={1.5} alignItems="flex-start">
                <Button
                  size="large"
                  variant="contained"
                  endIcon={<EastRoundedIcon />}
                  onClick={() =>
                    void loginWithRedirect({
                      appState: { returnTo },
                    })
                  }
                >
                  {t("auth.login.signIn")}
                </Button>

                <Typography variant="body2" color="text.secondary">
                  {t("auth.login.singleFlowHint")}
                </Typography>
              </Stack>
            </Stack>
          </Paper>

          <Paper
            elevation={0}
            sx={{
              p: { xs: 3, md: 4 },
              borderRadius: "12px",
              border: "1px solid rgba(17, 97, 73, 0.10)",
              bgcolor: "rgba(255, 253, 247, 0.92)",
              position: { xs: "static", xl: "sticky" },
              top: { xl: 24 },
            }}
          >
            <Stack spacing={3}>
              <Box>
                <Typography
                  variant="overline"
                  sx={{ color: "secondary.main", fontWeight: 800, letterSpacing: "0.18em" }}
                >
                  {t("auth.login.panelOverline")}
                </Typography>
                <Typography variant="h4" sx={{ mt: 0.75, mb: 1 }}>
                  {t("auth.login.panelTitle")}
                </Typography>
                <Typography color="text.secondary">{t("auth.login.panelDescription")}</Typography>
              </Box>

              <Stack spacing={2.25}>
                <HighlightRow
                  icon={<LocalParkingRoundedIcon />}
                  title={t("auth.login.featureMap.title")}
                  description={t("auth.login.featureMap.description")}
                />
                <HighlightRow
                  icon={<BoltRoundedIcon />}
                  title={t("auth.login.featureLive.title")}
                  description={t("auth.login.featureLive.description")}
                />
                <HighlightRow
                  icon={<InsightsRoundedIcon />}
                  title={t("auth.login.featureHistory.title")}
                  description={t("auth.login.featureHistory.description")}
                />
              </Stack>

              <Box
                sx={{
                  p: 2.5,
                  borderRadius: "10px",
                  border: "1px solid rgba(17, 97, 73, 0.12)",
                  bgcolor: "rgba(17, 97, 73, 0.04)",
                }}
              >
                <Typography sx={{ fontWeight: 800, mb: 0.75 }}>{t("auth.login.note.title")}</Typography>
                <Typography color="text.secondary">{t("auth.login.note.body")}</Typography>
              </Box>
            </Stack>
          </Paper>
        </Box>
      </Container>
    </Box>
  );
}
