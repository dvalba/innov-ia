import { HttpClient, httpResource } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { Idea, IdeaCola } from '../../../shared/types/models';

/**
 * Validation API client (T-051, RF-14/RF-15/RF-16).
 *
 * Reads the review queue through `httpResource` (guideline §5) and encapsulates
 * the two specialist mutations (approve `POST /validation/{id}/approve`,
 * reject `POST /validation/{id}/reject`) with `HttpClient`. It only consumes
 * the `validation` (G10) contracts — it never changes them. Errors are rethrown
 * so the screen surfaces the backend message (RNF-3); the reject endpoint keeps
 * the mandatory-comment 400 (case 13) untouched (RNF).
 */
@Injectable({ providedIn: 'root' })
export class ValidationService {
  private readonly http = inject(HttpClient);

  /** GET /validation/queue — SOLICITANDO_PUBLICACION ideas, oldest first. */
  readonly cola = httpResource<IdeaCola[]>(() => '/validation/queue');

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
}
