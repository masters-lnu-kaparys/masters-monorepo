import { useState } from "react";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import LogoutRoundedIcon from "@mui/icons-material/LogoutRounded";
import MenuRoundedIcon from "@mui/icons-material/MenuRounded";
import { AppBar, Box, Button, Container, Divider, Drawer, IconButton, Stack, Toolbar, Typography } from "@mui/material";
import { Link as RouterLink, Outlet, useLocation } from "react-router-dom";
import { APP_ROUTES } from "../app/routes";
import { useI18n } from "../i18n/LanguageProvider";
import { LanguageSwitcher } from "./LanguageSwitcher";

type AppShellProps = {
  isAdmin: boolean;
  userName: string;
  onLogout: () => void;
};

function NavButton({
  to,
  label,
  active,
  fullWidth = false,
  onClick,
}: {
  to: string;
  label: string;
  active: boolean;
  fullWidth?: boolean;
  onClick?: () => void;
}) {
  return (
    <Button
      component={RouterLink}
      to={to}
      fullWidth={fullWidth}
      onClick={onClick}
      variant={active ? "contained" : "text"}
      color={active ? "primary" : "inherit"}
      sx={{
        minHeight: { xs: 38, sm: 40 },
        minWidth: 0,
        px: { xs: 1.4, sm: 1.8 },
        borderRadius: "10px",
        color: active ? undefined : "text.primary",
        fontSize: { xs: "0.86rem", sm: "0.9rem" },
        fontWeight: 800,
        justifyContent: fullWidth ? "flex-start" : "center",
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </Button>
  );
}

export function AppShell({ isAdmin, userName, onLogout }: AppShellProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();
  const { t } = useI18n();

  const navItems = [
    {
      to: APP_ROUTES.home,
      label: t("common.map"),
      active: location.pathname === APP_ROUTES.home,
    },
    ...(isAdmin
      ? [
          {
            to: APP_ROUTES.admin,
            label: t("common.adminPanel"),
            active: location.pathname.startsWith(APP_ROUTES.admin),
          },
        ]
      : []),
  ];

  const closeMobileMenu = () => setMobileMenuOpen(false);
  const handleLogout = () => {
    closeMobileMenu();
    onLogout();
  };

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
        <Toolbar disableGutters sx={{ py: { xs: 0.85, md: 1.1 }, minHeight: "auto" }}>
          <Container maxWidth={false} sx={{ px: { xs: 2, sm: 3, md: 4 } }}>
            <Box
              sx={{
                display: { xs: "flex", md: "none" },
                alignItems: "center",
                justifyContent: "space-between",
                gap: 1.5,
              }}
            >
              <Typography
                variant="h6"
                noWrap
                sx={{
                  minWidth: 0,
                  fontSize: { xs: "1.28rem", sm: "1.35rem" },
                  fontWeight: 800,
                  lineHeight: 1.1,
                }}
              >
                {t("shell.appName")}
              </Typography>

              <IconButton
                aria-label={t("common.menu")}
                onClick={() => setMobileMenuOpen(true)}
                sx={{
                  width: 42,
                  height: 42,
                  border: "1px solid rgba(17, 97, 73, 0.18)",
                  borderRadius: "12px",
                  color: "primary.main",
                  bgcolor: "rgba(255, 253, 247, 0.86)",
                }}
              >
                <MenuRoundedIcon />
              </IconButton>
            </Box>

            <Box
              sx={{
                display: { xs: "none", md: "grid" },
                gridTemplateColumns: "auto minmax(0, 1fr) auto",
                alignItems: "center",
                columnGap: 2,
              }}
            >
              <Box sx={{ minWidth: 0 }}>
                <Typography
                  variant="h6"
                  noWrap
                  sx={{
                    fontSize: "1.28rem",
                    fontWeight: 800,
                    lineHeight: 1.1,
                  }}
                >
                  {t("shell.appName")}
                </Typography>
              </Box>

              <Stack
                direction="row"
                spacing={1}
                useFlexGap
                alignItems="center"
                sx={{ minWidth: 0 }}
              >
                {navItems.map((item) => (
                  <NavButton key={item.to} to={item.to} label={item.label} active={item.active} />
                ))}
              </Stack>

              <Stack
                direction="row"
                spacing={1}
                alignItems="center"
                justifyContent="flex-end"
                sx={{ minWidth: 0 }}
              >
                <Box sx={{ flexShrink: 0 }}>
                  <LanguageSwitcher compact />
                </Box>

                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    display: { xs: "none", sm: "block" },
                    maxWidth: { sm: 150, lg: 220 },
                    fontWeight: 600,
                    px: { xs: 0.25, sm: 0.5 },
                  }}
                  noWrap
                >
                  {userName}
                </Typography>

                <Button
                  variant="text"
                  startIcon={<LogoutRoundedIcon />}
                  onClick={onLogout}
                  aria-label={t("common.signOut")}
                  sx={{
                    minWidth: 0,
                    px: { xs: 1, sm: 1.2 },
                    py: 0.8,
                    borderRadius: "10px",
                    color: "primary.main",
                    fontWeight: 700,
                    whiteSpace: "nowrap",
                    "& .MuiButton-startIcon": {
                      mr: 0.8,
                      ml: 0,
                    },
                    "&:hover": {
                      bgcolor: "rgba(17, 97, 73, 0.08)",
                    },
                  }}
                >
                  {t("common.signOut")}
                </Button>
              </Stack>
            </Box>
          </Container>
        </Toolbar>
      </AppBar>

      <Drawer
        anchor="right"
        open={mobileMenuOpen}
        onClose={closeMobileMenu}
        ModalProps={{ keepMounted: true }}
        slotProps={{
          paper: {
            sx: {
              width: { xs: "min(86vw, 340px)", sm: 360 },
              p: 2.25,
              bgcolor: "rgba(253, 251, 247, 0.98)",
            },
          },
        }}
      >
        <Stack spacing={2.25} sx={{ height: "100%" }}>
          <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1.5}>
            <Typography variant="h6" sx={{ fontWeight: 800 }}>
              {t("shell.appName")}
            </Typography>
            <IconButton
              aria-label={t("common.closeMenu")}
              onClick={closeMobileMenu}
              sx={{
                border: "1px solid rgba(17, 97, 73, 0.14)",
                borderRadius: "12px",
                color: "primary.main",
              }}
            >
              <CloseRoundedIcon />
            </IconButton>
          </Stack>

          <Divider />

          <Stack spacing={1}>
            {navItems.map((item) => (
              <NavButton
                key={item.to}
                to={item.to}
                label={item.label}
                active={item.active}
                fullWidth
                onClick={closeMobileMenu}
              />
            ))}
          </Stack>

          <LanguageSwitcher />

          <Divider />

          <Stack spacing={1.25} sx={{ minWidth: 0 }}>
            <Typography variant="body2" color="text.secondary" noWrap>
              {userName}
            </Typography>
            <Button
              variant="contained"
              fullWidth
              startIcon={<LogoutRoundedIcon />}
              onClick={handleLogout}
              sx={{
                justifyContent: "flex-start",
                minHeight: 42,
                borderRadius: "10px",
                fontWeight: 800,
              }}
            >
              {t("common.signOut")}
            </Button>
          </Stack>
        </Stack>
      </Drawer>

      <Outlet />
    </Box>
  );
}
