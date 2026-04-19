import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { PropsWithChildren } from "react";
import { DEFAULT_LANGUAGE, getLocaleTag, LANGUAGE_STORAGE_KEY, normalizeLanguage, resolveInitialLanguage, type AppLanguage } from "./config";
import { translate } from "./messages";

type TranslationParams = Record<string, string | number>;

type I18nContextValue = {
  language: AppLanguage;
  locale: string;
  setLanguage: (language: AppLanguage) => void;
  t: (key: string, params?: TranslationParams) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

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

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);

  if (!context) {
    return {
      language: DEFAULT_LANGUAGE,
      locale: getLocaleTag(DEFAULT_LANGUAGE),
      setLanguage: () => {},
      t: (key, params) => translate(DEFAULT_LANGUAGE, key, params),
    };
  }

  return context;
}
