import { Button, ButtonGroup } from "@mui/material";
import { useI18n } from "../i18n/LanguageProvider";

export function LanguageSwitcher() {
  const { language, setLanguage, t } = useI18n();

  return (
    <ButtonGroup size="small" variant="outlined" aria-label="language switcher">
      <Button
        variant={language === "uk" ? "contained" : "outlined"}
        onClick={() => setLanguage("uk")}
      >
        {t("common.language.uk")}
      </Button>
      <Button
        variant={language === "en" ? "contained" : "outlined"}
        onClick={() => setLanguage("en")}
      >
        {t("common.language.en")}
      </Button>
    </ButtonGroup>
  );
}
