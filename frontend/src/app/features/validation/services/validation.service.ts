import { HttpClient, httpResource } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import {
  CriterioEvaluacion,
  Decision,
  Idea,
  IdeaCola,
  IdeaState,
  QueueStage,
} from '../../../shared/types/models';

/** `POST /validation/{id}/decision` payload (RF-27, plan §4.8). */
export interface ResultadoDecision {
  state: IdeaState;
  decision: Decision;
}

/**
 * Validation API client (T-051, RF-14/RF-15/RF-16; T-084, RF-14/RF-26/RF-27).
 *
 * Reads the review queue through `httpResource` (guideline §5) with a
 * stage-aware URL: `?stage=publicacion|calibracion` (v2.2, RF-14) — the
 * `etapa` signal drives the resource so the queue refires on every stage
 * switch. The mutations are encapsulated with `HttpClient` (never
 * `httpResource`): the two publication decisions (approve
 * `POST /validation/{id}/approve`, reject `POST /validation/{id}/reject`)
 * and the three calibration decisions (accept the AI evaluation
 * `POST /validation/{id}/evaluation/accept`, replace it
 * `POST /validation/{id}/evaluation`, decide
 * `POST /validation/{id}/decision`). It only consumes the `validation` (G10)
 * contracts — it never changes them. Errors are rethrown so the screen
 * surfaces the backend message (RNF-3); the backend stays the authority for
 * every rule (403/400/409/422).
 */
@Injectable({ providedIn: 'root' })
export class ValidationService {
  private readonly http = inject(HttpClient);

  /** The active queue stage (v2.2: `publicacion` | `calibracion`). */
  readonly etapa = signal<QueueStage>('publicacion');

  /**
   * GET /validation/queue?stage=… — the stage's ideas (RF-14 v2.2):
   * `SOLICITANDO_PUBLICACION` for publication, the calibration queue for
   * calibration. Refires whenever `etapa` changes.
   */
  readonly cola = httpResource<IdeaCola[]>(
    () => `/validation/queue?stage=${this.etapa()}`,
  );

  /** Switches the active queue stage (the resource refires). */
  cambiarEtapa(stage: QueueStage): void {
    this.etapa.set(stage);
  }

  /** POST /validation/{id}/approve — publish (VALIDADA_PUBLICA, rastro + `IDEA_PUBLISHED`). */
  aprobar(ideaId: string): Promise<Idea> {
    return firstValueFrom(this.http.post<Idea>(`/validation/${ideaId}/approve`, {}));
  }

  /**
   * POST /validation/{id}/reject — send back to EN_DESARROLLO with the mandatory
   * expert comment (case 13: the backend 400s a blank comment).
   */
  rechazar(ideaId: string, comment: string): Promise<Idea> {
    return firstValueFrom(this.http.post<Idea>(`/validation/${ideaId}/reject`, { comment }));
  }

  /**
   * POST /validation/{id}/evaluation/accept — accepts the AI evaluation as the
   * final judgment (status `ACEPTADA`, audited; 409 when it does not exist).
   */
  aceptarEvaluacion(ideaId: string): Promise<Idea> {
    return firstValueFrom(this.http.post<Idea>(`/validation/${ideaId}/evaluation/accept`, {}));
  }

  /**
   * POST /validation/{id}/evaluation — replaces the final judgment with the
   * specialist's own over the 5 fixed criteria (status `SUSTITUIDA`; 422 with
   * `details.problems` on missing/unknown/duplicated criteria or a score
   * out of 1-10, RNF-5). No state guard (case 23).
   */
  sustituirEvaluacion(ideaId: string, criteria: CriterioEvaluacion[]): Promise<Idea> {
    return firstValueFrom(this.http.post<Idea>(`/validation/${ideaId}/evaluation`, { criteria }));
  }

  /**
   * POST /validation/{id}/decision — records the final decision (RF-27):
   * `state` + the audited `decision` (409 `DECISION_MISMATCH` when the outcome
   * does not match the band, 400 `DECISION_REASON_REQUIRED` for a missing
   * reason on ARCHIVADA/RECHAZADA).
   */
  decidir(
    ideaId: string,
    outcome: Decision['outcome'],
    reason: string | null,
  ): Promise<ResultadoDecision> {
    return firstValueFrom(
      this.http.post<ResultadoDecision>(`/validation/${ideaId}/decision`, {
        outcome,
        reason,
      }),
    );
  }
}
