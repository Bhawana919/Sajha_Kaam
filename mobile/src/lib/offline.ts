// Slow or no internet: TanStack Query pauses and retries when the connection returns,
// and drafts live in AsyncStorage so a closed app or a dead battery loses nothing.
import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo, { useNetInfo } from '@react-native-community/netinfo';
import { onlineManager } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';

onlineManager.setEventListener((setOnline) =>
  NetInfo.addEventListener((state) => setOnline(state.isConnected !== false)),
);

/** True only when the device reports no connection (unknown counts as online). */
export function useOffline(): boolean {
  return useNetInfo().isConnected === false;
}

/**
 * State that survives app restarts. Drafts only: never tokens or anything sensitive.
 * `restored` is true when a saved draft was loaded, so the screen can say so.
 */
export function useDraft<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(initial);
  const [restored, setRestored] = useState(false);
  const loaded = useRef(false);
  const storageKey = `sajha-draft:${key}`;

  useEffect(() => {
    let alive = true;
    AsyncStorage.getItem(storageKey)
      .then((raw) => {
        if (alive && raw) {
          setValue(JSON.parse(raw) as T);
          setRestored(true);
        }
      })
      .catch(() => undefined)
      .finally(() => {
        loaded.current = true;
      });
    return () => {
      alive = false;
    };
  }, [storageKey]);

  const set = useCallback(
    (next: T | ((prev: T) => T)) => {
      setValue((prev) => {
        const v = typeof next === 'function' ? (next as (p: T) => T)(prev) : next;
        if (loaded.current) void AsyncStorage.setItem(storageKey, JSON.stringify(v)).catch(() => undefined);
        return v;
      });
    },
    [storageKey],
  );

  const clear = useCallback(() => {
    setValue(initial);
    setRestored(false);
    void AsyncStorage.removeItem(storageKey).catch(() => undefined);
    // initial is a fresh literal each render; the key is what identifies the draft
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storageKey]);

  return { value, set, restored, clear };
}
