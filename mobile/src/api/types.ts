// Friendly names for the generated OpenAPI types (npm run api:types after backend changes).
import type { components } from './schema';

type S = components['schemas'];

export type BoardCard = S['BoardCard'];
export type BoardPage = S['BoardPage'];
export type CardDetail = S['CardDetail'];
export type KaamCardDraft = S['KaamCardDraft'];
export type DraftResponse = S['DraftResponse'];
export type BlindReview = S['BlindReview'];
export type BlindApplicant = S['BlindApplicant'];
export type CardWrite = S['CardWrite'];
export type OwnerCard = S['OwnerCard'];
export type MyCardItem = S['MyCardItem'];
export type PostResult = S['PostResult'];
export type RuleIssue = S['RuleIssue'];
export type PickOut = S['PickOut'];
export type RevealOut = S['RevealOut'];
export type MyApplication = S['MyApplication'];
export type EngagementOut = S['EngagementOut'];
export type MessageOut = S['MessageOut'];
export type PassportOut = S['PassportOut'];
export type NotificationOut = S['NotificationOut'];
export type TranslateResponse = S['TranslateResponse'];
export type TokenPair = S['TokenPair'];
export type SampleIdentity = S['SampleIdentity'];
export type Me = S['Me'];
export type Skill = { id: string; en: string; ne: string };

export type BoardFilters = { pahilo?: boolean; skill?: string; q?: string };
export type ShareOut = S['ShareOut'];
export type ClaimOut = S['ClaimOut'];
export type StressResult = S['StressResult'];
