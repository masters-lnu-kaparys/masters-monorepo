import { Box, Button } from "@mui/material";
import { useI18n } from "../i18n/context";

type LanguageSwitcherProps = {
  compact?: boolean;
};

export function LanguageSwitcher({ compact = false }: LanguageSwitcherProps) {
  const { language, setLanguage, t } = useI18n();

  const options = [
    { key: "uk", label: t("common.language.uk") },
    { key: "en", label: t("common.language.en") },
  ] as const;

  return (
    <Box
      aria-label="language switcher"
      sx={{
        position: "relative",
        display: "inline-grid",
        gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
        alignItems: "stretch",
        p: 0.5,
        minWidth: compact ? 164 : 188,
        borderRadius: "999px",
        border: "1px solid rgba(17, 97, 73, 0.16)",
        bgcolor: "rgba(255, 253, 247, 0.92)",
        boxShadow: "0 8px 24px rgba(15, 23, 42, 0.06)",
        overflow: "hidden",
        isolation: "isolate",
        "&::before": {
          content: '""',
          position: "absolute",
          top: 4,
          bottom: 4,
          left: 4,
          width: "calc(50% - 4px)",
          borderRadius: "999px",
          bgcolor: "primary.main",
          boxShadow: "0 8px 18px rgba(17, 97, 73, 0.22)",
          transform: language === "uk" ? "translateX(0%)" : "translateX(100%)",
          transition: "transform 220ms ease, background-color 220ms ease, box-shadow 220ms ease",
          zIndex: 0,
        },
      }}
    >
      {options.map((option) => {
        const selected = language === option.key;

        return (
          <Button
            key={option.key}
            size="small"
            variant="text"
            onClick={() => setLanguage(option.key)}
            sx={{
              position: "relative",
              zIndex: 1,
              minWidth: 0,
              px: compact ? 1.25 : 1.6,
              py: compact ? 0.7 : 0.8,
              borderRadius: "999px",
              color: selected ? "common.white" : "text.secondary",
              bgcolor: "transparent",
              fontSize: compact ? "0.8rem" : "0.86rem",
              fontWeight: selected ? 800 : 700,
              lineHeight: 1.1,
              transition: "color 180ms ease, transform 180ms ease",
              "&:hover": {
                bgcolor: "transparent",
                color: selected ? "common.white" : "text.primary",
              },
            }}
          >
            {option.label}
          </Button>
        );
      })}
    </Box>
  );
}
