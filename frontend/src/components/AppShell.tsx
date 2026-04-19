import LogoutRoundedIcon from "@mui/icons-material/LogoutRounded";
import { AppBar, Box, Button, Container, Stack, Toolbar, Typography } from "@mui/material";
import { Link as RouterLink, Outlet, useLocation } from "react-router-dom";
import { APP_ROUTES } from "../app/routes";
import { useI18n } from "../i18n/LanguageProvider";
import { LanguageSwitcher } from "./LanguageSwitcher";

type AppShellProps = {
  isAdmin: boolean;
  userName: string;
  onLogout: () => void;
};

function NavButton({ to, label, active }: { to: string; label: string; active: boolean }) {
  return (
    <Button
      component={RouterLink}
      to={to}
      variant={active ? "contained" : "text"}
      color={active ? "primary" : "inherit"}
      sx={{ color: active ? undefined : "text.primary" }}
    >
      {label}
    </Button>
  );
}

export function AppShell({ isAdmin, userName, onLogout }: AppShellProps) {
  const location = useLocation();
  const { t } = useI18n();

  return (
    <Box sx={{ minHeight: "100vh" }}>
      <AppBar
        position="sticky"
        color="transparent"
        elevation={0}
        sx={{
          backdropFilter: "blur(16px)",
          borderBottom: "1px solid rgba(17, 97, 73, 0.10)",
          bgcolor: "rgba(253, 251, 247, 0.84)",
        }}
      >
        <Toolbar sx={{ py: 1.25 }}>
          <Container maxWidth={false} sx={{ px: { xs: 0, md: 1 } }}>
            <Stack
              direction={{ xs: "column", lg: "row" }}
              justifyContent="space-between"
              alignItems={{ xs: "stretch", lg: "center" }}
              spacing={1.5}
            >
              <Stack direction={{ xs: "column", md: "row" }} spacing={1.25} alignItems={{ xs: "stretch", md: "center" }}>
                <Typography variant="h6" sx={{ fontWeight: 800 }}>
                  {t("shell.appName")}
                </Typography>

                <Stack direction="row" spacing={1} flexWrap="wrap">
                  <NavButton
                    to={APP_ROUTES.home}
                    label={t("common.map")}
                    active={location.pathname === APP_ROUTES.home}
                  />
                  {isAdmin ? (
                    <NavButton
                      to={APP_ROUTES.admin}
                      label={t("common.adminPanel")}
                      active={location.pathname.startsWith(APP_ROUTES.admin)}
                    />
                  ) : null}
                </Stack>
              </Stack>

              <Stack
                direction={{ xs: "column", sm: "row" }}
                spacing={1}
                alignItems={{ xs: "stretch", sm: "center" }}
              >
                <LanguageSwitcher compact />

                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ maxWidth: 220, fontWeight: 600, px: { xs: 0.25, sm: 0.5 } }}
                  noWrap
                >
                  {userName}
                </Typography>

                <Button
                  variant="text"
                  startIcon={<LogoutRoundedIcon />}
                  onClick={onLogout}
                  sx={{
                    px: 1.2,
                    py: 0.8,
                    borderRadius: "999px",
                    color: "primary.main",
                    fontWeight: 700,
                    "&:hover": {
                      bgcolor: "rgba(17, 97, 73, 0.08)",
                    },
                  }}
                >
                  {t("common.signOut")}
                </Button>
              </Stack>
            </Stack>
          </Container>
        </Toolbar>
      </AppBar>

      <Outlet />
    </Box>
  );
}
