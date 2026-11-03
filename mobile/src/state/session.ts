// Session tokens: expo-secure-store on phones; the browser's storage on web (no secure store there).
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';
import { create } from 'zustand';

const KEY = 'sajha-session';

export type Tokens = { access_token: string; refresh_token: string };

const storage = {
  get: () => (Platform.OS === 'web' ? AsyncStorage.getItem(KEY) : SecureStore.getItemAsync(KEY)),
  set: (v: string) => (Platform.OS === 'web' ? AsyncStorage.setItem(KEY, v) : SecureStore.setItemAsync(KEY, v)),
  clear: () => (Platform.OS === 'web' ? AsyncStorage.removeItem(KEY) : SecureStore.deleteItemAsync(KEY)),
};

type Session = {
  tokens: Tokens | null;
  loaded: boolean;
  load: () => Promise<void>;
  save: (t: Tokens) => Promise<void>;
  clear: () => Promise<void>;
};

export const useSession = create<Session>()((set) => ({
  tokens: null,
  loaded: false,
  load: async () => {
    try {
      const raw = await storage.get();
      set({ tokens: raw ? (JSON.parse(raw) as Tokens) : null, loaded: true });
    } catch {
      set({ tokens: null, loaded: true });
    }
  },
  save: async (tokens) => {
    set({ tokens });
    await storage.set(JSON.stringify(tokens));
  },
  clear: async () => {
    set({ tokens: null });
    await storage.clear();
  },
}));
