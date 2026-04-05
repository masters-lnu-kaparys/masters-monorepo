import { Auth0Provider } from "@auth0/auth0-react";
import { BrowserRouter } from "react-router-dom";
import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "leaflet/dist/leaflet.css";
import App from "./App";
import { getAuth0RuntimeConfig } from "./auth/config";
import { FullScreenStatus } from "./components/FullScreenStatus";
import "./index.css";

const theme = createTheme({
  palette: {
    primary: {
      main: "#116149",
      light: "#2f8f6e",
      dark: "#0b4634",
    },
    secondary: {
      main: "#d97706",
    },
    background: {
      default: "#f7f3ea",
      paper: "#fffdf7",
    },
    success: {
      main: "#2f8f6e",
    },
    warning: {
      main: "#d97706",
    },
    error: {
      main: "#c2410c",
    },
  },
  typography: {
    fontFamily: '"Manrope", "Segoe UI", sans-serif',
    h1: {
      fontWeight: 800,
      letterSpacing: "-0.04em",
    },
    h2: {
      fontWeight: 800,
      letterSpacing: "-0.03em",
    },
    h3: {
      fontWeight: 700,
      letterSpacing: "-0.02em",
    },
  },
  shape: {
    borderRadius: 18,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 999,
          textTransform: "none",
          fontWeight: 700,
          boxShadow: "none",
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          boxShadow: "0 18px 48px rgba(30, 41, 59, 0.08)",
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 999,
          fontWeight: 700,
        },
      },
    },
  },
});

const auth0Config = getAuth0RuntimeConfig();

const root = (
  <StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {auth0Config ? (
        <Auth0Provider
          domain={auth0Config.domain}
          clientId={auth0Config.clientId}
          cacheLocation="localstorage"
          useRefreshTokens
          authorizationParams={{
            redirect_uri: window.location.origin,
            audience: auth0Config.audience,
            scope: "openid profile email",
          }}
          onRedirectCallback={(appState) => {
            const nextPath = typeof appState?.returnTo === "string"
              ? appState.returnTo
              : window.location.pathname;

            window.history.replaceState({}, document.title, nextPath);
          }}
        >
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </Auth0Provider>
      ) : (
        <FullScreenStatus
          title="Потрібно налаштувати Auth0"
          description="Додай VITE_AUTH0_DOMAIN, VITE_AUTH0_CLIENT_ID і VITE_AUTH0_AUDIENCE у frontend env, а також Auth0:Domain і Auth0:Audience у backend appsettings."
          severity="warning"
        />
      )}
    </ThemeProvider>
  </StrictMode>
);

createRoot(document.getElementById("root")!).render(root);
