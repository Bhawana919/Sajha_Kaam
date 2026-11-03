// UI preferences that survive restarts. Non-sensitive only (AsyncStorage);
// the session token goes in expo-secure-store once auth lands.
import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import type { Locale, Numerals } from '@/lib/format';

export type Role = 'client' | 'worker' | 'guest';

type Prefs = {
  locale: Locale | null; // null until chosen; defaults from the device locale
  numerals: Numerals;
  role: Role | null;
  /** Lite Mode: text-first, no illustrations beyond a small mark, no animation. */
  lite: boolean;
  setLite: (v: boolean) => void;
  setLocale: (l: Locale) => void;
  setNumerals: (n: Numerals) => void;
  setRole: (r: Role | null) => void;
};

export const usePrefs = create<Prefs>()(
  persist(
    (set) => ({
      locale: null,
      numerals: 'devanagari',
      role: null,
      lite: false,
      setLite: (lite) => set({ lite }),
      setLocale: (locale) => set({ locale }),
      setNumerals: (numerals) => set({ numerals }),
      setRole: (role) => set({ role }),
    }),
    {
      name: 'sajha-prefs',
      storage: createJSONStorage(() => AsyncStorage),
      partialize: ({ locale, numerals, role, lite }) => ({ locale, numerals, role, lite }),
    },
  ),
);
