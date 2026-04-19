import AdminPanelSettingsRoundedIcon from "@mui/icons-material/AdminPanelSettingsRounded";
import LogoutRoundedIcon from "@mui/icons-material/LogoutRounded";
import MapRoundedIcon from "@mui/icons-material/MapRounded";
import { AppBar, Box, Button, Chip, Container, Stack, Toolbar, Typography } from "@mui/material";
import { Link as RouterLink, Outlet, useLocation } from "react-router-dom";
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
                  <NavButton to="/" label={t("common.map")} active={location.pathname === "/"} />
                  {isAdmin ? (
                    <NavButton
                      to="/admin"
                      label={t("common.adminPanel")}
                      active={location.pathname.startsWith("/admin")}
                    />
                  ) : null}
                </Stack>
              </Stack>

              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25} alignItems={{ xs: "stretch", sm: "center" }}>
                <LanguageSwitcher />
                <Chip
                  color={isAdmin ? "secondary" : "primary"}
                  icon={isAdmin ? <AdminPanelSettingsRoundedIcon /> : <MapRoundedIcon />}
                  label={isAdmin ? t("common.role.admin") : t("common.role.user")}
                />
                <Typography color="text.secondary" sx={{ maxWidth: 220 }} noWrap>
                  {userName}
                </Typography>
                <Button variant="outlined" startIcon={<LogoutRoundedIcon />} onClick={onLogout}>
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
