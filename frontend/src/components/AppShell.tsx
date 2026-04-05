import AdminPanelSettingsRoundedIcon from "@mui/icons-material/AdminPanelSettingsRounded";
import LogoutRoundedIcon from "@mui/icons-material/LogoutRounded";
import MapRoundedIcon from "@mui/icons-material/MapRounded";
import { AppBar, Box, Button, Chip, Container, Stack, Toolbar, Typography } from "@mui/material";
import { Link as RouterLink, Outlet, useLocation } from "react-router-dom";

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
                  Smart Parking
                </Typography>

                <Stack direction="row" spacing={1} flexWrap="wrap">
                  <NavButton to="/" label="Карта" active={location.pathname === "/"} />
                  {isAdmin ? (
                    <NavButton
                      to="/admin"
                      label="Адмін-панель"
                      active={location.pathname.startsWith("/admin")}
                    />
                  ) : null}
                </Stack>
              </Stack>

              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25} alignItems={{ xs: "stretch", sm: "center" }}>
                <Chip
                  color={isAdmin ? "secondary" : "primary"}
                  icon={isAdmin ? <AdminPanelSettingsRoundedIcon /> : <MapRoundedIcon />}
                  label={isAdmin ? "Роль: Admin" : "Роль: User"}
                />
                <Typography color="text.secondary" sx={{ maxWidth: 220 }} noWrap>
                  {userName}
                </Typography>
                <Button variant="outlined" startIcon={<LogoutRoundedIcon />} onClick={onLogout}>
                  Вийти
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
