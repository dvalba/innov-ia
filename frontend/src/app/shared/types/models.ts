/**
 * Shared TypeScript contract mirroring the backend JSON payloads (plan §2).
 *
 * Types are the exact mirror of the JSON schemas in plan §2 so every feature
 * works on the same contract (RNF-2). UI copy stays in Spanish (RNF-4).
 */

/** A user account as returned by `POST /auth/login` and `GET /auth/me` (§2 user). */
export interface Usuario {
  id: string;
  username: string;
  name: string;
  area: string;
  contact: string;
  roles: string[];
  active: boolean;
  shouldChangePassword: boolean;
  createdAt: string;
}

/** Role names (spec §5 / plan §3.1). A user without roles cannot access platform features. */
export const ROLE_PROPOSER = 'proponente';
export const ROLE_VALIDATOR = 'especialista';
export const ROLE_ADMIN = 'admin';

/** Idea life-cycle states (plan §2.2 / §4.6, RNF-9). */
export type IdeaState = 'EN_DESARROLLO' | 'SOLICITANDO_PUBLICACION' | 'VALIDADA_PUBLICA';

/** How the idea was created (RF-2 / RNF-2). */
export type IdeaOrigin = 'asistida' | 'manual';

/** Conversation state (plan §2.4). */
export type ConversationState = 'ACTIVA' | 'RESUMEN' | 'TERMINADA' | 'CONTINGENCIA';

/** Origin of an `IdeaVersion` (RF-11 / RF-8 / RF-13). */
export type VersionRequestedBy = 'refinement' | 'improvement' | 'adjustment';

/** Decision state of an `IdeaVersion` (RF-8 / RF-13). */
export type VersionStatus = 'PENDIENTE' | 'ACEPTADA' | 'DESCARTADA' | 'VIGENTE';

/** The only four in-app notification events (RF-18). */
export type NotificacionType =
  | 'IDEA_REFINED'
  | 'IDEA_PUBLISHED'
  | 'IDEA_REJECTED'
  | 'IDEA_REQUESTED';

/** Speaker of a chat message (plan §2.3). */
export type ChatRole = 'user' | 'assistant' | 'system';

/** Title suggestion actions (RF-4). */
export type TituloAction = 'accept' | 'another' | 'manual';

/** Campo 2: proponent info, prefilled from the account (RF-6/RF-7). */
export interface Proponente {
  name: string;
  area: string;
  contact: string;
}

/** The 6 mandatory idea fields (plan §2.2, RNF-5). */
export interface IdeaFields {
  title: string;
  proponent: Proponente;
  description: string;
  problem: string;
  expectedBenefit: string;
  strategicAlignment: string;
}

/** Expert rejection note (RF-16, RNF-8, case 13): who rejected, when, why. */
export interface NotaRechazo {
  by: string;
  byName: string;
  comment: string;
  at: string;
}

/** A saved pending improvement request (case 10, plan §4.5), stored on the idea. */
export interface SolicitudMejora {
  instruction: string;
  requestedBy: string;
  requestedAt: string;
}

/** `Idea` entity (plan §2.2): the 6 fields + ownership, origin, state and audit. */
export interface Idea extends IdeaFields {
  id: string;
  ownerId: string;
  origin: IdeaOrigin;
  state: IdeaState;
  reviewedByAI: boolean;
  currentVersionId: string | null;
  createdAt: string;
  requestDate: string | null;
  publishedAt: string | null;
  publishedBy: string | null;
  /** The expert's rejection note when the idea was rejected (RF-16, T-050). */
  rejectionNote: NotaRechazo | null;
  /** `true` while the assistant is producing a version (manual edit blocked, RNF-9). */
  generando: boolean;
  /** A pending AI improvement request when the IA was unavailable (case 10, RF-8). */
  improvementRequest: SolicitudMejora | null;
}

/** `GET /ideas/me` entry (RF-19): the "Mis ideas" summary. */
export interface IdeaResumen {
  id: string;
  title: string;
  createdAt: string;
  origin: IdeaOrigin;
  state: IdeaState;
}

/** `GET /ideas/{id}` payload (RF-19): the idea plus its versions (oldest first). */
export interface IdeaDetalle {
  idea: Idea;
  versions: IdeaVersion[];
}

/** Proactive title suggestion block (RF-4, plan §2.3). */
export interface SugerenciaTitulo {
  text: string;
  actions: TituloAction[];
}

/** Chat message of a capture conversation (plan §2.3). */
export interface ChatMessage {
  id: string;
  conversationId: string;
  role: ChatRole;
  text: string;
  currentField: string | null;
  quickOptions: string[];
  titleSuggestion: SugerenciaTitulo | null;
  needsClarification: boolean;
  createdAt: string;
}

/** Capture conversation (plan §2.4). */
export interface Conversation {
  id: string;
  userId: string;
  state: ConversationState;
  capturedFields: Record<string, string>;
  currentField: string;
  order: string[];
  createdAt: string;
}

/** Pending/refined version of an idea (plan §2.5). */
export interface IdeaVersion {
  id: string;
  ideaId: string;
  version: number;
  fields: IdeaFields;
  requestedBy: VersionRequestedBy;
  status: VersionStatus;
  createdAt: string;
}

/** Campo 2 reduced to public visibility (RF-14/RF-20): name + area, no contact. */
export interface ProponentePublico {
  name: string;
  area: string;
}

/**
 * The 6 idea fields in their public visibility (queue + catalog, RF-14/RF-20):
 * identical to `IdeaFields` but the proponent is reduced to name/area.
 */
export interface IdeaFieldsPublica {
  title: string;
  proponent: ProponentePublico;
  description: string;
  problem: string;
  expectedBenefit: string;
  strategicAlignment: string;
}

/** `GET /validation/queue` entry (RF-14): a SOLICITANDO_PUBLICACION idea. */
export interface IdeaCola {
  id: string;
  origin: IdeaOrigin;
  requestDate: string | null;
  fields: IdeaFieldsPublica;
}

/** `GET /catalog/public` entry (RF-20): a VALIDADA_PUBLICA idea, read-only. */
export interface IdeaCatalogo {
  id: string;
  origin: IdeaOrigin;
  createdAt: string;
  publishedAt: string | null;
  fields: IdeaFieldsPublica;
}

/** `GET /notifications` payload (RF-18): the list + the unread counter. */
export interface NotificacionListado {
  notifications: Notificacion[];
  unread: number;
}

/** In-app notification (plan §2.7, RF-18). */
export interface Notificacion {
  id: string;
  userId: string;
  type: NotificacionType;
  ideaId: string;
  message: string;
  read: boolean;
  createdAt: string;
}
