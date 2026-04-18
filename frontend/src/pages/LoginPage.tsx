import { useAuth0 } from "@auth0/auth0-react";
import BoltRoundedIcon from "@mui/icons-material/BoltRounded";
import EastRoundedIcon from "@mui/icons-material/EastRounded";
import LocalParkingRoundedIcon from "@mui/icons-material/LocalParkingRounded";
import SecurityRoundedIcon from "@mui/icons-material/SecurityRounded";
import TuneRoundedIcon from "@mui/icons-material/TuneRounded";
import {
  Box,
  Button,
  Chip,
  Container,
  Divider,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

type DetailCardProps = {
  icon: ReactNode;
  title: string;
  description: string;
};

type AccessStepProps = {
  accent: string;
  icon: ReactNode;
  title: string;
  description: string;
};

function DetailCard({ icon, title, description }: DetailCardProps) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.5,
        height: "100%",
        borderRadius: 4,
        border: "1px solid rgba(17, 97, 73, 0.10)",
        bgcolor: "rgba(255, 255, 255, 0.62)",
      }}
    >
      <Stack spacing={2}>
        <Box
          sx={{
            width: 46,
            height: 46,
            display: "grid",
            placeItems: "center",
            borderRadius: 2.5,
            bgcolor: "rgba(17, 97, 73, 0.08)",
            color: "primary.main",
          }}
        >
          {icon}
        </Box>

        <Box>
          <Typography variant="h6" sx={{ mb: 1, fontWeight: 800 }}>
            {title}
          </Typography>
          <Typography color="text.secondary">{description}</Typography>
        </Box>
      </Stack>
    </Paper>
  );
}

function AccessStep({ accent, icon, title, description }: AccessStepProps) {
  return (
    <Box
      sx={{
        p: 2.5,
        borderRadius: 4,
        border: "1px solid rgba(17, 97, 73, 0.10)",
        bgcolor: "rgba(255, 255, 255, 0.58)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          position: "absolute",
          left: 0,
          top: 0,
          bottom: 0,
          width: 4,
          bgcolor: accent,
        }}
      />

      <Stack direction="row" spacing={1.75} alignItems="flex-start">
        <Box
          sx={{
            width: 42,
            height: 42,
            display: "grid",
            placeItems: "center",
            borderRadius: 2.5,
            bgcolor: `${accent}18`,
            color: accent,
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
    </Box>
  );
}

export function LoginPage() {
  const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0();
  const location = useLocation();
  const returnTo = typeof location.state?.returnTo === "string" ? location.state.returnTo : "/";

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
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", xl: "minmax(0, 1.2fr) minmax(360px, 0.8fr)" },
            gap: 3,
            alignItems: "start",
          }}
        >
          <Paper
            elevation={0}
            sx={{
              p: { xs: 3, md: 5 },
              borderRadius: 5,
              border: "1px solid rgba(17, 97, 73, 0.10)",
              bgcolor: "rgba(255, 252, 245, 0.78)",
              backdropFilter: "blur(14px)",
            }}
          >
            <Stack spacing={4}>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25} alignItems={{ xs: "flex-start", sm: "center" }}>
                <Chip label="SMART PARKING PLATFORM" color="secondary" sx={{ letterSpacing: "0.12em" }} />
                <Chip label="Auth0 Protected Access" variant="outlined" />
              </Stack>

              <Box sx={{ maxWidth: 820 }}>
                <Typography
                  variant="h1"
                  sx={{
                    fontSize: { xs: "2.85rem", md: "4.5rem" },
                    lineHeight: { xs: 1, md: 0.96 },
                    mb: 2,
                  }}
                >
                  Контроль паркування в реальному міському контексті
                </Typography>
                <Typography
                  sx={{
                    maxWidth: 720,
                    fontSize: { xs: "1rem", md: "1.12rem" },
                    color: "text.secondary",
                  }}
                >
                  Увійди, щоб бачити карту парковок, вільні місця та оновлення від IoT-сенсорів у
                  реальному часі. Базовий доступ отримує кожен автентифікований користувач, а
                  адмінські інструменти відкриваються тільки після призначення ролі Admin в Auth0
                  Dashboard.
                </Typography>
              </Box>

              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
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
                  Увійти до системи
                </Button>
                <Button
                  size="large"
                  variant="outlined"
                  onClick={() =>
                    void loginWithRedirect({
                      authorizationParams: { screen_hint: "signup" },
                      appState: { returnTo },
                    })
                  }
                >
                  Створити обліковий запис
                </Button>
              </Stack>

              <Divider />

              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" },
                  gap: 1.5,
                }}
              >
                <DetailCard
                  icon={<LocalParkingRoundedIcon />}
                  title="Карта парковок"
                  description="Завантаженість місць і доступність парковок у межах міста на одній інтерактивній карті."
                />
                <DetailCard
                  icon={<BoltRoundedIcon />}
                  title="Оновлення наживо"
                  description="Система поєднує фізичний сенсор і симуляцію, щоб дати стабільну live-картину для демонстрації."
                />
                <DetailCard
                  icon={<SecurityRoundedIcon />}
                  title="Ролі без плутанини"
                  description="Кожен авторизований користувач має базовий доступ, а додаткові функції дає тільки роль Admin."
                />
              </Box>
            </Stack>
          </Paper>

          <Paper
            elevation={0}
            sx={{
              p: { xs: 3, md: 4 },
              borderRadius: 5,
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
                  ACCESS MODEL
                </Typography>
                <Typography variant="h4" sx={{ mt: 0.75, mb: 1 }}>
                  Як працює доступ
                </Typography>
                <Typography color="text.secondary">
                  Логіка проста: звичайний користувач одразу отримує доступ до карти, а адмінські
                  можливості відкриваються лише тим, кому їх реально призначили.
                </Typography>
              </Box>

              <Stack spacing={1.5}>
                <AccessStep
                  accent="#116149"
                  icon={<TuneRoundedIcon />}
                  title="User за замовчуванням"
                  description="Після успішного входу користувач одразу бачить карту, стан парковок і історію місць без додаткових ручних налаштувань."
                />
                <AccessStep
                  accent="#d97706"
                  icon={<SecurityRoundedIcon />}
                  title="Admin лише через Auth0 Dashboard"
                  description="Якщо користувачу призначають роль Admin в Auth0, у нього з'являється доступ до адмін-панелі та CRUD-операцій."
                />
              </Stack>

              <Paper
                elevation={0}
                sx={{
                  p: 2.25,
                  borderRadius: 4,
                  border: "1px dashed rgba(17, 97, 73, 0.18)",
                  bgcolor: "rgba(17, 97, 73, 0.04)",
                }}
              >
                <Typography sx={{ fontWeight: 800, mb: 0.75 }}>Що важливо знати</Typography>
                <Stack spacing={0.75}>
                  <Typography variant="body2" color="text.secondary">
                    Якщо роль щойно змінили в Auth0, достатньо вийти й увійти повторно, щоб оновився токен.
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Базовий доступ не вимагає явного призначення ролі User для кожного нового акаунта.
                  </Typography>
                </Stack>
              </Paper>
            </Stack>
          </Paper>
        </Box>
      </Container>
    </Box>
  );
}
