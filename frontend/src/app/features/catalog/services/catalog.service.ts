import { HttpClient, HttpResourceRef, httpResource } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import {
  CatalogoZonas,
  CriterioEvaluacion,
  Debate,
  Idea,
  IdeaDetallePublica,
  MensajeDebate,
} from '../../../shared/types/models';

/**
   * Public catalog API client (T-052, T-077, T-085, RF-20/RF-23/RF-24/RF-25/RF-26).
   *
   * Reads go through `httpResource` (guideline §5): the public catalog by the
   * four zones (RF-20), the per-idea public detail and the per-idea debate. The
   * mutations (`POST .../debate`,
 * `PUT .../debate/deadline`, the two evaluation decisions) are encapsulated
 * with `HttpClient` (guideline §5: mutations never use `httpResource`). The
 * evaluation endpoints live on `/validation` but they belong to this
 * self-contained public detail — kept here so the catalog feature imports no
 * other feature (RNF-2). Errors are rethrown so the screens surface the
 * backend message (RNF-3).
 */
/** `POST /catalog/{id}/debate` payload (RF-25): the posted message, the
 * assistant's reply (when a valid `@asistant` invocation) and the debate. */
export interface ResultadoDebate {
  message: MensajeDebate;
  assistantReply: MensajeDebate | null;
  debate: Debate;
}

@Injectable({ providedIn: 'root' })
export class CatalogService {
  private readonly http = inject(HttpClient);

  /**
   * GET /catalog/public — the four zones (RF-20) as a name -> compact-items map.
   * Read without `?zone=` so one request feeds every tab; the per-zone form
   * (`?zone=…`) is still served by the backend (T-083) for direct use.
   */
  readonly catalogoZonas = httpResource<CatalogoZonas>(() => '/catalog/public');

  /**
   * Builds a reactive `GET /catalog/{id}` resource for a given idea (RF-23:
   * 6 fields + evaluations). Used by the detail page, which reads its `:id`
   * once from the route; 404 for unknown/unpublished ids.
   */
  detallePublico(ideaId: string): HttpResourceRef<IdeaDetallePublica | undefined> {
    return httpResource<IdeaDetallePublica>(() => `/catalog/${ideaId}`);
  }

  /**
   * Builds a reactive `GET /catalog/{id}/debate` resource (RF-24). Used by the
   * detail page; the first read at/after the deadline closes the debate,
   * generates the summary and retries a pending `@asistant` request.
   */
  debateDe(ideaId: string): HttpResourceRef<Debate | undefined> {
    return httpResource<Debate>(() => `/catalog/${ideaId}/debate`);
  }

  /**
   * POST /catalog/{id}/debate — posts a message in the open debate (201). A
   * valid `@asistant` invocation may bring the assistant's reply; a closed
   * debate is a 409, a dangling link a 400 (cases 18-20).
   */
  publicarMensaje(
    ideaId: string,
    text: string,
    linkedMessageId: string | null,
  ): Promise<ResultadoDebate> {
    return firstValueFrom(
      this.http.post<ResultadoDebate>(`/catalog/${ideaId}/debate`, { text, linkedMessageId }),
    );
  }

  /**
   * POST /validation/{id}/evaluation/accept — the AI evaluation becomes the
   * final judgment (`status=ACEPTADA`, case 23); 409 when there is no AI
   * evaluation yet (case 22). Returns the updated idea payload.
   */
  aceptarEvaluacion(ideaId: string): Promise<Idea> {
    return firstValueFrom(this.http.post<Idea>(`/validation/${ideaId}/evaluation/accept`, {}));
  }

  /**
   * POST /validation/{id}/evaluation — replaces the final judgment with the
   * specialist's own (status=SUSTITUIDA, case 23); 422 when the criteria are
   * not exactly the 5 fixed ones. Returns the updated idea payload.
   */
  sustituirEvaluacion(ideaId: string, criteria: CriterioEvaluacion[]): Promise<Idea> {
    return firstValueFrom(this.http.post<Idea>(`/validation/${ideaId}/evaluation`, { criteria }));
  }
}
