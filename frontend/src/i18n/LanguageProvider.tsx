import { useEffect, useMemo, useState } from "react";
import type { PropsWithChildren } from "react";
import { getLocaleTag, LANGUAGE_STORAGE_KEY, normalizeLanguage, resolveInitialLanguage, type AppLanguage } from "./config";
import { translate } from "./messages";
import { I18nContext, type I18nContextValue } from "./context";

export function LanguageProvider({ children }: PropsWithChildren) {
  const [language, setLanguageState] = useState<AppLanguage>(resolveInitialLanguage());

  useEffect(() => {
    const normalized = normalizeLanguage(language);
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, normalized);
    document.documentElement.lang = normalized;
  }, [language]);

  const value = useMemo<I18nContextValue>(() => ({
    language,
    locale: getLocaleTag(language),
    setLanguage: setLanguageState,
    t: (key, params) => translate(language, key, params),
  }), [language]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}
