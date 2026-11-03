// i18next setup. First launch picks Nepali for ne* device locales, else English;
// the user's choice (ने | EN) is saved and wins after that.
import { getLocales } from 'expo-localization';
import i18n from 'i18next';
import { useCallback } from 'react';
import { initReactI18next, useTranslation } from 'react-i18next';

import { localDigits, type Locale } from '@/lib/format';
import { usePrefs } from '@/state/prefs';

import en from './en.json';
import ne from './ne.json';

export function deviceLocale(): Locale {
  try {
    return getLocales()[0]?.languageCode?.startsWith('ne') ? 'ne' : 'en';
  } catch {
    return 'en';
  }
}

// eslint-disable-next-line import/no-named-as-default-member
i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, ne: { translation: ne } },
  lng: deviceLocale(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  returnNull: false,
});

export function applyLocale(locale: Locale) {
  // eslint-disable-next-line import/no-named-as-default-member
  if (i18n.language !== locale) void i18n.changeLanguage(locale);
}

/**
 * t() with numerals applied: in Nepali, digits in the translated text become Devanagari
 * unless the user chose Latin digits. Never interpolate money into t(); render it with money().
 */
export function useT() {
  const { t, i18n: inst } = useTranslation();
  const numerals = usePrefs((s) => s.numerals);
  const locale = (inst.language === 'ne' ? 'ne' : 'en') as Locale;
  const tt = useCallback(
    (key: string, opts?: Record<string, unknown>) => localDigits(t(key, opts) as string, locale, numerals),
    [t, locale, numerals],
  );
  /** Pick the right side of a bilingual {x_ne, x_en} pair. */
  const pick = useCallback(
    (ne: string, en: string) => (locale === 'ne' ? ne || en : en || ne),
    [locale],
  );
  /** Country names come from the client's profile in English; show a Nepali name when we have one. */
  const country = useCallback(
    (name: string) => (inst.exists(`country.${name}`) ? (t(`country.${name}`) as string) : name),
    [t, inst],
  );
  return { t: tt, locale, numerals, pick, country, digits: (v: string | number) => localDigits(v, locale, numerals) };
}

export default i18n;
