export type AppLanguage = "uk" | "en";

export const DEFAULT_LANGUAGE: AppLanguage = "uk";
export const LANGUAGE_STORAGE_KEY = "smart-parking.language";

export function normalizeLanguage(value: string | null | undefined): AppLanguage {
  if (!value) {
    return DEFAULT_LANGUAGE;
  }

  return value.toLowerCase().startsWith("en") ? "en" : "uk";
}

export function resolveInitialLanguage(): AppLanguage {
  if (typeof window === "undefined") {
    return DEFAULT_LANGUAGE;
  }

  const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  if (stored) {
    return normalizeLanguage(stored);
  }

  return normalizeLanguage(window.navigator.language);
}

export function getStoredLanguage(): AppLanguage {
  return resolveInitialLanguage();
}

export function getLocaleTag(language: AppLanguage): string {
  return language === "uk" ? "uk-UA" : "en-US";
}
