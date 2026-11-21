import { Auth0Provider } from "@auth0/auth0-react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import { createRoot } from "react-dom/client";
import "leaflet/dist/leaflet.css";
import App from "./App";
import { APP_ROUTES } from "./app/routes";
import { SamplingDemoPage } from "./pages/SamplingDemoPage";
import { AUTH_CALLBACK_PATH, getAuth0RuntimeConfig } from "./auth/config";
import { FullScreenStatus } from "./components/FullScreenStatus";
import { LanguageProvider } from "./i18n/LanguageProvider";
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
    borderRadius: 6,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: "8px",
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
          borderRadius: "8px",
          fontWeight: 700,
        },
      },
    },
    MuiButtonGroup: {
      styleOverrides: {
        grouped: {
          borderRadius: "8px",
        },
      },
    },
  },
});

const auth0Config = getAuth0RuntimeConfig();

const root = (
  <ThemeProvider theme={theme}>
    <CssBaseline />
    <LanguageProvider>
      <BrowserRouter>
        <Routes>
          <Route path={APP_ROUTES.samplingDemo} element={<SamplingDemoPage />} />
          <Route path="/*" element={auth0Config ? (
        <Auth0Provider
          domain={auth0Config.domain}
          clientId={auth0Config.clientId}
          cacheLocation="localstorage"
          useRefreshTokens
          useRefreshTokensFallback
          authorizationParams={{
            redirect_uri: `${window.location.origin}${AUTH_CALLBACK_PATH}`,
            audience: auth0Config.audience,
            scope: "openid profile email offline_access",
          }}
          onRedirectCallback={(appState) => {
            const nextPath = typeof appState?.returnTo === "string"
              ? appState.returnTo
              : "/";

            window.history.replaceState({}, document.title, nextPath);
          }}
        >
          <App />
        </Auth0Provider>
      ) : (
        <FullScreenStatus
          titleKey="app.auth0Missing.title"
          descriptionKey="app.auth0Missing.description"
          severity="warning"
        />
      )} />
        </Routes>
      </BrowserRouter>
    </LanguageProvider>
  </ThemeProvider>
);

createRoot(document.getElementById("root")!).render(root);
