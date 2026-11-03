// HTTP client with the session token and one automatic refresh on 401.
// No EXPO_PUBLIC_API_URL (or EXPO_PUBLIC_USE_MOCK=1) -> read-only mock mode from backend-generated fixtures.
import { mockRequest } from '@/mocks';
import { useSession } from '@/state/session';

import { ApiError } from './errors';

export { ApiError };

const API_URL = process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, '');
export const USE_MOCK = process.env.EXPO_PUBLIC_USE_MOCK === '1' || !API_URL;
export const PUBLIC_BASE = API_URL ?? '';
const TIMEOUT_MS = 15000;

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

/** Read the server's `detail` (string code, message, or object such as Leak Guard findings). */
export function errorDetail(e: unknown): unknown {
  return e instanceof ApiError ? e.detail : null;
}

let refreshing: Promise<boolean> | null = null;

async function refresh(): Promise<boolean> {
  const tokens = useSession.getState().tokens;
  if (!tokens) return false;
  try {
    const res = await fetch(`${API_URL}/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: tokens.refresh_token }),
    });
    if (!res.ok) {
      await useSession.getState().clear();
      return false;
    }
    await useSession.getState().save(await res.json());
    return true;
  } catch {
    return false;
  }
}

export async function api<T>(
  path: string,
  init: { method?: Method; body?: unknown; idempotencyKey?: string; auth?: boolean } = {},
): Promise<T> {
  const method = init.method ?? 'GET';
  if (USE_MOCK) return mockRequest<T>(method, path, init.body);

  const send = async () => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
    const token = useSession.getState().tokens?.access_token;
    try {
      return await fetch(`${API_URL}${path}`, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...(token && init.auth !== false ? { Authorization: `Bearer ${token}` } : {}),
          ...(init.idempotencyKey ? { 'Idempotency-Key': init.idempotencyKey } : {}),
        },
        body: init.body === undefined ? undefined : JSON.stringify(init.body),
        signal: controller.signal,
      });
    } catch {
      throw new ApiError('network', 0, 'network');
    } finally {
      clearTimeout(timer);
    }
  };

  let res = await send();
  if (res.status === 401 && useSession.getState().tokens && init.auth !== false) {
    refreshing ??= refresh().finally(() => (refreshing = null));
    if (await refreshing) res = await send();
  }
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      detail = ((await res.json()) as { detail?: unknown }).detail ?? detail;
    } catch {
      // keep statusText
    }
    throw new ApiError('http', res.status, detail);
  }
  return (await res.json()) as T;
}

/** A fresh key per user action, so a double tap or a retry never applies twice. */
export function newIdempotencyKey(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}
