// Mock API backed by fixtures.json (regenerate: backend/scripts/export_fixtures.py).
import { ApiError } from '@/api/errors';
import type { BoardCard, BoardPage, DraftResponse } from '@/api/types';

import fixtures from './fixtures.json';

const LATENCY_MS = 250;
const shiftMs = Date.now() - new Date(fixtures.generated_at).getTime();

function rebase<T extends { window_closes_at?: string | null }>(item: T): T {
  if (!item.window_closes_at) return item;
  return { ...item, window_closes_at: new Date(new Date(item.window_closes_at).getTime() + shiftMs).toISOString() };
}

function matches(card: BoardCard, params: URLSearchParams): boolean {
  if (params.get('pahilo') === 'true' && !card.pahilo_kaam) return false;
  const skill = params.get('skill');
  if (skill && card.skill !== skill) return false;
  const q = params.get('q')?.trim().toLowerCase();
  if (q) {
    const s = fixtures.skills.find((k) => k.id === card.skill);
    const hay = [card.title_en.toLowerCase(), card.title_ne, s?.en.toLowerCase(), s?.ne].join(' ');
    if (!hay.includes(q)) return false;
  }
  return true;
}

function route(method: string, path: string, body: unknown): unknown {
  const [pathname, query = ''] = path.split('?');
  const params = new URLSearchParams(query);

  if (method === 'GET' && pathname === '/v1/skills') return fixtures.skills;
  if (method === 'GET' && pathname === '/v1/board') {
    const items = (fixtures.board.items as BoardCard[]).filter((c) => matches(c, params)).map(rebase);
    return { items, next_cursor: null } satisfies BoardPage;
  }
  const m = pathname.match(/^\/v1\/cards\/([^/]+)$/);
  if (method === 'GET' && m) {
    const card = (fixtures.cards as Record<string, BoardCard>)[m[1]];
    if (!card) throw Object.assign(new Error('not found'), { status: 404 });
    return rebase(card);
  }
  if (method === 'POST' && pathname === '/v1/cards/draft') {
    const text = String((body as { text?: string })?.text ?? '');
    const drafts = fixtures.drafts as Record<string, DraftResponse>;
    // Mock mode only knows the fixture requests; anything else gets the Dashain card.
    return drafts[text] ?? Object.values(drafts)[0];
  }
  // Signing in, posting, applying and the rest of the loop need the real backend.
  throw new ApiError('mock', 0, 'needs_backend');
}

export async function mockRequest<T>(method: string, path: string, body?: unknown): Promise<T> {
  await new Promise((r) => setTimeout(r, LATENCY_MS));
  return route(method, path, body) as T;
}
