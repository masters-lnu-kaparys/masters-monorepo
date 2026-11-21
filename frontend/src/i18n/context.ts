import { createContext, useContext } from "react";
import { DEFAULT_LANGUAGE, getLocaleTag, type AppLanguage } from "./config";
import { translate } from "./messages";

type TranslationParams = Record<string, string | number>;
export type I18nContextValue = {
  language: AppLanguage;
  locale: string;
  setLanguage: (language: AppLanguage) => void;
  t: (key: string, params?: TranslationParams) => string;
};
export const I18nContext = createContext<I18nContextValue | null>(null);
export function useI18n(): I18nContextValue {
  return useContext(I18nContext) ?? {
    language: DEFAULT_LANGUAGE,
    locale: getLocaleTag(DEFAULT_LANGUAGE),
    setLanguage: () => {},
    t: (key, params) => translate(DEFAULT_LANGUAGE, key, params),
  };
}
