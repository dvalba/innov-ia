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

/** Idea life-cycle states (plan §2.2 / §4.6, RNF-9; v2.2 adds the three final states). */
export type IdeaState =
  | 'EN_DESARROLLO'
  | 'SOLICITANDO_PUBLICACION'
  | 'VALIDADA_PUBLICA'
  | 'ACEPTADA'
  | 'ARCHIVADA'
  | 'RECHAZADA';

/** The three possible final outcomes of the calibration decision (RF-27). */
export type DecisionOutcome = 'ACEPTADA' | 'ARCHIVADA' | 'RECHAZADA';

/** The final calibration decision recorded on an idea (RF-27/RF-29, plan §2.2/§4.6). */
export interface Decision {
  outcome: DecisionOutcome;
  reason: string | null;
  score: number;
  decidedBy: string;
  decidedByName: string;
  decidedAt: string;
}

/** The two review-queue stages (RF-14, v2.2: `GET /validation/queue?stage=…`). */
export type QueueStage = 'publicacion' | 'calibracion';

/** How the idea was created (RF-2 / RNF-2). */
export type IdeaOrigin = 'asistida' | 'manual';

/** Conversation state (plan §2.4). */
export type ConversationState = 'ACTIVA' | 'RESUMEN' | 'TERMINADA' | 'CONTINGENCIA';

/** Origin of an `IdeaVersion` (RF-11 / RF-8 / RF-13). */
export type VersionRequestedBy = 'refinement' | 'improvement' | 'adjustment';

/** Decision state of an `IdeaVersion` (RF-8 / RF-13). */
export type VersionStatus = 'PENDIENTE' | 'ACEPTADA' | 'DESCARTADA' | 'VIGENTE';

/** The in-app notification events (RF-18; v2.2 adds the final-state ones). */
export type NotificacionType =
  | 'IDEA_REFINED'
  | 'IDEA_PUBLISHED'
  | 'IDEA_REJECTED'
  | 'IDEA_REQUESTED'
  | 'IDEA_ACCEPTED'
  | 'IDEA_ARCHIVED'
  | 'IDEA_REEVALUATED'
  | 'IDEA_CALIBRATION_PENDING';

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
  /** The final judgment (RF-26); present once the evaluation exists (T-077). */
  evaluation?: Evaluacion | null;
  /** The immutable evaluation snapshot produced by the AI (RF-26, T-077). */
  aiEvaluation?: Evaluacion | null;
  /** The final calibration decision (RF-27/RF-29); present in the final states. */
  decision?: Decision | null;
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

/**
 * The four public-catalog zones (RF-20) in their canonical tab order (D21):
 * each zone is a projection of one idea state.
 */
export const CATALOG_ZONES = [
  'en-proceso',
  'aceptadas',
  'rechazadas',
  'archivadas',
] as const;

/** One of the four catalog zone names (the `?zone=` query value, RF-20). */
export type CatalogZone = (typeof CATALOG_ZONES)[number];

/** Spanish label of a catalog zone (RNF-4). */
export const ZONA_LABEL: Record<CatalogZone, string> = {
  'en-proceso': 'En proceso',
  aceptadas: 'Aceptadas',
  rechazadas: 'Rechazadas',
  archivadas: 'Archivadas',
};

/**
 * `GET /catalog/public` compact entry (RF-20, D16): one idea in a zone, holding
 * only `id`, `title`, `publishedAt` and `description` (read-only, no contact).
 */
export interface ItemZona {
  id: string;
  title: string;
  publishedAt: string | null;
  description: string;
}

/** `GET /catalog/public` (no zone, RF-20): the four zones as a name -> items map. */
export interface CatalogoZonas {
  zones: Record<CatalogZone, ItemZona[]>;
}

/** `GET /catalog/public?zone=…` (one zone, RF-20). */
export interface CatalogoZona {
  zone: CatalogZone;
  items: ItemZona[];
}

/** Evaluation lifecycle state (`evaluation.status`, plan §2.2, RF-26). */
export type EvaluacionEstado = 'PENDING' | 'GENERADA' | 'ACEPTADA' | 'SUSTITUIDA';

/** One of the 5 fixed criteria of the final judgment (RF-26, RNF-5). */
export interface CriterioEvaluacion {
  criterion: string;
  score: number;
  justification: string;
}

/**
 * An idea evaluation (plan §2.2): the final judgment `evaluation` and the
 * immutable AI snapshot `aiEvaluation` share this shape. `PENDING` (case 22)
 * carries only `status` — the AI could not generate it yet.
 */
export interface Evaluacion {
  status: EvaluacionEstado;
  criteria?: CriterioEvaluacion[];
  author?: string;
  createdAt?: string;
  decidedBy?: string | null;
  decidedAt?: string | null;
}

/** `GET /catalog/{ideaId}` payload (T-077, RF-23; v2.2 adds state + decision). */
export interface IdeaDetallePublica {
  id: string;
  fields: IdeaFieldsPublica;
  origin: IdeaOrigin;
  createdAt: string;
  publishedAt: string | null;
  state: IdeaState;
  decision: Decision | null;
  evaluation: Evaluacion | null;
  aiEvaluation: Evaluacion | null;
}

/** `GET /admin/calibration-thresholds` payload (RF-28). */
export interface CalibrationThresholds {
  rejectionThreshold: number;
  acceptanceThreshold: number;
  updatedBy?: string | null;
  updatedAt?: string | null;
}

/** One message of the published-idea debate (plan §2.8, RF-24/RF-25). */
export interface MensajeDebate {
  id: string;
  ideaId: string;
  authorId: string;
  authorName: string;
  text: string;
  createdAt: string;
  linkedMessageId: string | null;
  isAssistant: boolean;
  processed: boolean;
}

/** A pending `@asistant` request the assistant could not process (case 20). */
export interface SolicitudPendienteAsistente {
  messageId: string;
  request: string;
  at: string;
}

/** One admin adjustment of the debate deadline (audit, RNF-11). */
export interface AjusteFechaLimite {
  by: string;
  byName: string;
  at: string;
  before: string;
  after: string;
}

/** The debate of a published idea (plan §2.8, RF-24). */
export interface Debate {
  id: string;
  ideaId: string;
  deadline: string;
  open: boolean;
  closed: boolean;
  closedAt: string | null;
  closedBy: string | null;
  summary: string | null;
  summaryAt: string | null;
  pendingAssistant: SolicitudPendienteAsistente | null;
  deadlineHistory: AjusteFechaLimite[];
  messages: MensajeDebate[];
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
