import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { PublicKey } from '@/lib/proof';
import { useSession } from '@/state/session';

import { api, newIdempotencyKey } from './client';
import type {
  BlindReview,
  BoardFilters,
  BoardPage,
  CardDetail,
  ClaimOut,
  CardWrite,
  DraftResponse,
  KaamCardDraft,
  EngagementOut,
  Me,
  MessageOut,
  MyApplication,
  MyCardItem,
  NotificationOut,
  OwnerCard,
  PassportOut,
  PickOut,
  PostResult,
  RevealOut,
  SampleIdentity,
  StressResult,
  ShareOut,
  Skill,
  TokenPair,
  TranslateResponse,
} from './types';

const signedIn = () => !!useSession.getState().tokens;

// ---------- session ----------

export function useMe() {
  const tokens = useSession((s) => s.tokens);
  return useQuery({ queryKey: ['me', tokens?.access_token], queryFn: () => api<Me>('/v1/me'), enabled: !!tokens });
}

export function useSampleIdentities() {
  return useQuery({
    queryKey: ['samples'],
    queryFn: () => api<SampleIdentity[]>('/v1/auth/sample-identities', { auth: false }),
    staleTime: Infinity,
  });
}

function useSignIn<T>(path: string) {
  const qc = useQueryClient();
  const save = useSession((s) => s.save);
  return useMutation({
    mutationFn: (body: T) => api<TokenPair>(path, { method: 'POST', body, auth: false }),
    onSuccess: async (tokens) => {
      await save(tokens);
      qc.clear();
    },
  });
}

export const useSampleLogin = () => useSignIn<{ user_id: string }>('/v1/auth/sample-login');
export const useLogin = () => useSignIn<{ email: string; password: string }>('/v1/auth/login');
export const useRegister = () => useSignIn<Record<string, unknown>>('/v1/auth/register');

export function useUpdateMe() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Pick<Me, 'locale' | 'numerals_pref' | 'skills'>>) =>
      api<Me>('/v1/me', { method: 'PATCH', body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me'] }),
  });
}

// ---------- board ----------

export function useSkills() {
  return useQuery({ queryKey: ['skills'], queryFn: () => api<Skill[]>('/v1/skills', { auth: false }), staleTime: Infinity });
}

export function useBoard(filters: BoardFilters) {
  const params = new URLSearchParams();
  if (filters.pahilo) params.set('pahilo', 'true');
  if (filters.skill) params.set('skill', filters.skill);
  if (filters.q?.trim()) params.set('q', filters.q.trim());
  const qs = params.toString();
  return useQuery({ queryKey: ['board', filters], queryFn: () => api<BoardPage>(`/v1/board${qs ? `?${qs}` : ''}`) });
}

export function useCard(id: string | undefined) {
  return useQuery({ queryKey: ['card', id], queryFn: () => api<CardDetail>(`/v1/cards/${id}`), enabled: !!id });
}

// ---------- client ----------

export function useDraftCard() {
  return useMutation({
    mutationFn: (text: string) => api<DraftResponse>('/v1/cards/draft', { method: 'POST', body: { text } }),
  });
}

export function useMyCards() {
  return useQuery({ queryKey: ['myCards'], queryFn: () => api<MyCardItem[]>('/v1/me/cards'), enabled: signedIn() });
}

export function useOwnerCard(id: string | undefined) {
  return useQuery({ queryKey: ['owner', id], queryFn: () => api<OwnerCard>(`/v1/cards/${id}/manage`), enabled: !!id });
}

/** Save (create or update) then post. Returns the post result with rule issues. */
export function useSaveAndPost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id?: string; body: CardWrite }) => {
      const card = id
        ? await api<OwnerCard>(`/v1/cards/${id}`, { method: 'PATCH', body })
        : await api<OwnerCard>('/v1/cards', { method: 'POST', body, idempotencyKey: newIdempotencyKey() });
      const result = await api<PostResult>(`/v1/cards/${card.id}/post`, {
        method: 'POST',
        idempotencyKey: newIdempotencyKey(),
      });
      return { cardId: card.id, result };
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['myCards'] }),
  });
}

/** Any card-level action; refreshes the owner view, review and lists afterwards. */
export function useCardAction<T = unknown>(cardId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ path, body }: { path: string; body?: unknown }) =>
      api<T>(path, { method: 'POST', body, idempotencyKey: newIdempotencyKey() }),
    onSuccess: () => {
      for (const key of [['owner', cardId], ['review', cardId], ['myCards'], ['board'], ['notifications']]) {
        void qc.invalidateQueries({ queryKey: key });
      }
    },
  });
}

export const usePick = (cardId: string | undefined) => useCardAction<PickOut>(cardId);
export const useReveal = (cardId: string | undefined) => useCardAction<RevealOut>(cardId);

export function useBlindReview(cardId: string | undefined) {
  return useQuery({
    queryKey: ['review', cardId],
    queryFn: () => api<BlindReview>(`/v1/cards/${cardId}/review`),
    enabled: !!cardId,
  });
}

export function useScore(cardId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ applicationId, stars }: { applicationId: string; stars: Record<string, number> }) =>
      api(`/v1/reviews/${applicationId}`, { method: 'PUT', body: { stars } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['review', cardId] }),
  });
}

// ---------- worker ----------

export function useApply(cardId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api<MyApplication>(`/v1/cards/${cardId}/applications`, { method: 'POST', body, idempotencyKey: newIdempotencyKey() }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['myApplications'] }),
  });
}

export function useLeakScan() {
  return useMutation({
    mutationFn: (text: string) =>
      api<{ findings: { kind: string; start: number; end: number; text: string }[]; redacted: string }>(
        '/v1/leakguard/scan',
        { method: 'POST', body: { text } },
      ),
  });
}

export function useMyApplications() {
  return useQuery({ queryKey: ['myApplications'], queryFn: () => api<MyApplication[]>('/v1/me/applications'), enabled: signedIn() });
}

export function useWithdraw() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api<MyApplication>(`/v1/applications/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['myApplications'] }),
  });
}

export function usePassport() {
  return useQuery({ queryKey: ['passport'], queryFn: () => api<PassportOut>('/v1/me/passport'), enabled: signedIn() });
}

// ---------- engagements (both roles) ----------

export function useMyEngagements() {
  return useQuery({ queryKey: ['engagements'], queryFn: () => api<EngagementOut[]>('/v1/engagements/me'), enabled: signedIn() });
}

export function useEngagement(id: string | undefined) {
  return useQuery({ queryKey: ['engagement', id], queryFn: () => api<EngagementOut>(`/v1/engagements/${id}`), enabled: !!id });
}

export function useEngagementAction(id: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ action, body }: { action: string; body?: unknown }) =>
      api<EngagementOut>(`/v1/engagements/${id}/${action}`, { method: 'POST', body, idempotencyKey: newIdempotencyKey() }),
    onSuccess: (data) => {
      qc.setQueryData(['engagement', id], data);
      for (const key of [['engagements'], ['myApplications'], ['myCards'], ['passport'], ['owner', data.card_id], ['notifications']]) {
        void qc.invalidateQueries({ queryKey: key });
      }
    },
  });
}

export function useMessages(id: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ['messages', id],
    queryFn: () => api<MessageOut[]>(`/v1/engagements/${id}/messages`),
    enabled: !!id && enabled,
    refetchInterval: 15000,
  });
}

export function useSendMessage(id: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { text: string; lang: string }) =>
      api<MessageOut>(`/v1/engagements/${id}/messages`, { method: 'POST', body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['messages', id] }),
  });
}

export function useMessageCheck() {
  return useMutation({
    mutationFn: (text: string) => api<string[]>('/v1/leakguard/message-check', { method: 'POST', body: { text } }),
  });
}

export function useOpenCase() {
  return useMutation({
    mutationFn: (body: { card_id: string; reason: string }) => api('/v1/cases', { method: 'POST', body }),
  });
}

// ---------- shared ----------

export function useNotifications() {
  const tokens = useSession((s) => s.tokens);
  return useQuery({
    queryKey: ['notifications'],
    queryFn: () => api<NotificationOut[]>('/v1/notifications'),
    enabled: !!tokens,
    refetchInterval: 30000,
  });
}

export function useReadAll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<number>('/v1/notifications/read-all', { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  });
}

export function useTranslate() {
  return useMutation({
    mutationFn: (body: { text: string; target: 'ne' | 'en' }) =>
      api<TranslateResponse>('/v1/translate', { method: 'POST', body }),
  });
}

export function useDemo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (path: string) => api(`/demo/${path}`, { method: 'POST', auth: false }),
    onSuccess: () => qc.invalidateQueries(),
  });
}

// ---------- Work Passport (worker) ----------

export function useSetVisibility() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, visibility }: { id: string; visibility: 'private' | 'public' }) =>
      api<ClaimOut>(`/v1/passport/claims/${id}`, { method: 'PATCH', body: { visibility } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['passport'] }),
  });
}

export function useShares() {
  return useQuery({ queryKey: ['shares'], queryFn: () => api<ShareOut[]>('/v1/passport/shares'), enabled: signedIn() });
}

export function useCreateShare() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (claimIds: string[]) =>
      api<ShareOut>('/v1/passport/shares', { method: 'POST', body: { claim_ids: claimIds, days: 7 } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['shares'] }),
  });
}

export function useRevokeShare() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api<ShareOut>(`/v1/passport/shares/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['shares'] }),
  });
}

export function useExportPassport() {
  return useMutation({ mutationFn: () => api<Record<string, unknown>>('/v1/passport/export') });
}

export function useDeleteMyData() {
  const qc = useQueryClient();
  const clear = useSession((s) => s.clear);
  return useMutation({
    mutationFn: () => api<{ deleted: boolean }>('/v1/me/data', { method: 'DELETE' }),
    onSuccess: async () => {
      await clear();
      qc.clear();
    },
  });
}

/** Sajha Kaam's public signing keys (for checking Passport records on the phone). */
export function useSigningKeys() {
  return useQuery({
    queryKey: ['signingKeys'],
    queryFn: () => api<{ keys: PublicKey[] }>('/.well-known/sajha-kaam-keys.json', { auth: false }),
    staleTime: Infinity,
  });
}

export function useStressTest() {
  return useMutation({
    mutationFn: (card: KaamCardDraft) => api<StressResult>('/v1/cards/stress-test', { method: 'POST', body: { card } }),
  });
}
