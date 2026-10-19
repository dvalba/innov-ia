import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { Conversation, IdeaFields, SugerenciaTitulo, TituloAction } from '../../../shared/types/models';

/** `GET /capture/assistant-status` (RF-7): availability probe. */
export interface AssistantStatus {
  status: 'OK' | 'UNAVAILABLE';
}

/** The assistant turn returned by a capture call (RF-3/RF-4/RF-5). */
export interface TurnAssistant {
  text: string;
  currentField: string | null;
  quickOptions: string[];
  titleSuggestion: SugerenciaTitulo | null;
  needsClarification?: boolean;
}

/** `POST /capture/start` (RF-2/RF-7) outcome. */
export interface StartResult {
  mode: 'assistant' | 'manual';
  resumed: boolean;
  conversation: Conversation | null;
  assistant: TurnAssistant | null;
  manual: { notice: string; capturedFields: Record<string, string> } | null;
}

/** `POST /capture/messages` (RF-3/RF-4/RF-5, RF-6) next turn. */
export interface MessageTurn {
  conversationId: string;
  state: 'ACTIVA' | 'RESUMEN';
  assistant?: TurnAssistant;
  summary?: Record<string, unknown>;
}

/** `POST /capture/title` (RF-4) outcome. */
export interface TitleTurn {
  conversationId: string;
  state: 'ACTIVA' | 'RESUMEN';
  assistant?: TurnAssistant;
  summary?: Record<string, unknown>;
}

/** `POST /capture/finish` (RF-6) outcome. */
export interface FinishResult {
  ideaId: string;
  state: string;
  origin: string;
}

/** `POST /capture/activate-manual` (RF-7, RNF-10) pre-filled payload. */
export interface ActivateManualResult {
  conversationId: string;
  state: string;
  capturedFields: Record<string, string>;
}

/** `POST /ideas` (RF-7, RNF-5) outcome: the registered idea payload (summary). */
export interface IdeaCreada {
  id: string;
  ownerId: string;
  origin: string;
  state: string;
}

/** The manual contingency payload (notice + captured fields, RNF-10). */
export interface Contingencia {
  notice: string;
  capturedFields: Record<string, string>;
}

/**
 * Capture API client + client-side conversation orchestration (T-040, RF-2..RF-7,
 * plan §1.1 "Orquestación client-side de la conversación").
 *
 * This is the single `HttpClient` wrapper for the `/capture` endpoints (Angular
 * guidelines §5). It also owns the shared conversation state (signals) so the
 * start screen (`new-idea`) and the chat (`chat-assist`) work on the same
 * in-memory conversation without a route parameter.
 *
 * `cargando` is `true` while any IA-backed call is in flight (RNF-3: visible
 * loading), so the UI can show "escribiendo…" during the model's reply.
 */
@Injectable({ providedIn: 'root' })
export class CaptureService {
  private readonly http = inject(HttpClient);

  /** Visible loading flag while an IA call is in flight (RNF-3). */
  readonly cargando = signal(false);

  /** The in-progress capture conversation, or `null` (no capture in flight). */
  readonly conversacionId = signal<string | null>(null);
  /** The current assistant turn (question + chips + title suggestion). */
  readonly turno = signal<TurnAssistant | null>(null);
  /** Conversation state: `ACTIVA` (in progress) or `RESUMEN` (6 fields closed). */
  readonly estadoConv = signal<'ACTIVA' | 'RESUMEN' | null>(null);
  /** The editable summary when the 6 fields close (RF-6). */
  readonly resumen = signal<Record<string, unknown> | null>(null);
  /** `true` when the capture was a resume of an existing ACTIVA (caso 8). */
  readonly retomada = signal(false);
  /** The manual contingency payload (RNF-10), when a manual fallback is active. */
  readonly contingencia = signal<Contingencia | null>(null);

  /** Wraps an IA call showing the RNF-3 visible loading flag. */
  private async conCarga<T>(call: () => Promise<T>): Promise<T> {
    this.cargando.set(true);
    try {
      return await call();
    } finally {
      this.cargando.set(false);
    }
  }

  /** GET /capture/assistant-status — availability probe (RF-7, caso 1). */
  async assistantStatus(): Promise<AssistantStatus> {
    return firstValueFrom(this.http.get<AssistantStatus>('/capture/assistant-status'));
  }

  /**
   * POST /capture/start — start or resume the capture conversation (RF-2,
   * caso 8). Stamps the shared state: the conversation, the opening turn and,
   * when the assistant is unavailable, the manual contingency (RF-7, caso 1).
   */
  iniciar(): Promise<StartResult> {
    return this.conCarga(async () => {
      const r = await firstValueFrom(this.http.post<StartResult>('/capture/start', null));
      if (r.mode === 'manual') {
        this.contingencia.set(r.manual ?? { notice: '', capturedFields: {} });
        return r;
      }
      this.conversacionId.set(r.conversation?.id ?? null);
      this.turno.set(r.assistant ?? null);
      this.estadoConv.set('ACTIVA');
      this.resumen.set(null);
      this.retomada.set(r.resumed);
      this.contingencia.set(null);
      return r;
    });
  }

  /**
   * POST /capture/messages — one user message: a chip (`quickOptionSelected`) or
   * a free narrative (`message`). On a mid-conversation IA failure (503) the
   * captured fields are kept as the manual contingency (RNF-10) and the error
   * is rethrown so the screen can react (RF-7, caso 2 — T-045).
   */
  enviar(conversationId: string, message?: string, quickOptionSelected?: string): Promise<MessageTurn> {
    return this.conCarga(async () => {
      let t: MessageTurn;
      try {
        t = await firstValueFrom(
          this.http.post<MessageTurn>('/capture/messages', {
            conversationId,
            message: message ?? null,
            quickOptionSelected: quickOptionSelected ?? null,
          }),
        );
      } catch (error) {
        this.onAsistenteDisponible(error);
        throw error;
      }
      this.turno.set(t.assistant ?? null);
      this.estadoConv.set(t.state);
      this.resumen.set(t.summary ?? null);
      return t;
    });
  }

  /**
   * POST /capture/title — apply a title action (RF-4): `accept`, `another` or
   * `manual` (stored unmodified).
   */
  accionTitulo(conversationId: string, action: TituloAction, manualText?: string): Promise<TitleTurn> {
    return this.conCarga(async () => {
      let t: TitleTurn;
      try {
        t = await firstValueFrom(
          this.http.post<TitleTurn>('/capture/title', {
            conversationId,
            action,
            manualText: manualText ?? null,
          }),
        );
      } catch (error) {
        this.onAsistenteDisponible(error);
        throw error;
      }
      this.turno.set(t.assistant ?? null);
      this.estadoConv.set(t.state);
      this.resumen.set(t.summary ?? null);
      return t;
    });
  }

  /**
   * POST /capture/finish — confirm the summary and register the idea (RF-6).
   * Clears the conversation state on success so a new capture can start.
   */
  finalizar(conversationId: string, captured: Record<string, unknown>): Promise<FinishResult> {
    return this.conCarga(async () => {
      const r = await firstValueFrom(
        this.http.post<FinishResult>('/capture/finish', { conversationId, captured }),
      );
      this.reiniciar();
      return r;
    });
  }

  /**
   * POST /capture/activate-manual — convert the capture into the pre-filled
   * manual form (RF-7, RNF-10).
   */
  activarManual(conversationId: string): Promise<ActivateManualResult> {
    return this.conCarga(async () => {
      const r = await firstValueFrom(
        this.http.post<ActivateManualResult>('/capture/activate-manual', { conversationId }),
      );
      this.contingencia.set({ notice: '', capturedFields: r.capturedFields });
      return r;
    });
  }

  /** Resets the in-memory conversation state (for a fresh capture). */
  reiniciar(): void {
    this.conversacionId.set(null);
    this.turno.set(null);
    this.estadoConv.set(null);
    this.resumen.set(null);
    this.retomada.set(false);
    this.contingencia.set(null);
  }

  /**
   * POST /ideas (RF-7, RNF-5) — register the manual idea (origin `manual`).
   * The 6 fields go as objects; the owner comes from the session. The 6-field
   * completeness and the contact format (case 12) are validated by the ideas
   * domain (a 422 leaves the form data untouched, caso 17).
   */
  async crearManual(campos: IdeaFields): Promise<IdeaCreada> {
    const r = await firstValueFrom(
      this.http.post<IdeaCreada>('/ideas', { ...campos, origin: 'manual' }),
    );
    this.reiniciar();
    return r;
  }

  /**
   * Extracts the manual-fallback fields from a 503 `ASSISTANT_UNAVAILABLE`
   * error and stores them as the contingency (RNF-10: nothing is lost). A
   * different error leaves the contingency untouched.
   */
  private onAsistenteDisponible(error: unknown): void {
    const body = error as {
      error?: { code?: string; message?: string };
      fallback?: { capturedFields?: Record<string, string> };
    };
    if (body?.error?.code === 'ASSISTANT_UNAVAILABLE') {
      this.contingencia.set({
        notice: body.error.message ?? 'El asistente no está disponible.',
        capturedFields: body.fallback?.capturedFields ?? {},
      });
    }
  }
}
