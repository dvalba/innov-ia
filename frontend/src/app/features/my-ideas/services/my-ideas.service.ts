import { HttpClient, HttpResourceRef, httpResource } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import {
  Idea,
  IdeaDetalle,
  IdeaFields,
  IdeaResumen,
  IdeaVersion,
  SolicitudMejora,
} from '../../../shared/types/models';

/** `POST /ideas/{id}/improve` outcome (RF-8): with the IA a pending version;
 * without it the case-10 notice (plan §4.5). */
export type MejoraResultado =
  | { version: IdeaVersion; idea: Idea }
  | { notice: string; improvementRequest: SolicitudMejora };

/**
 * "Mis ideas" API client (T-046..T-050, RF-19/RF-9/RF-8/RF-10/RF-16).
 *
 * Reads go through `httpResource` (guideline §5): the list and the per-idea
 * detail. The `/ideas/{id}` mutations (PUT edit, POST improve, POST decide,
 * POST request-publication) are encapsulated with `HttpClient`. This client only
 * consumes the `ideas` (G06) contracts — it never changes them. Errors are
 * rethrown so the screens surface the backend message.
 */
@Injectable({ providedIn: 'root' })
export class MyIdeasService {
  private readonly http = inject(HttpClient);

  /** GET /ideas/me — the proponent's own ideas, newest first (RF-19). */
  readonly miLista = httpResource<IdeaResumen[]>(() => '/ideas/me');

  /**
   * Builds a reactive `GET /ideas/{id}` resource for a given idea. Used by the
   * detail page, which reads its `:id` once from the route.
   */
  ideaDetalle(ideaId: string): HttpResourceRef<IdeaDetalle | undefined> {
    return httpResource<IdeaDetalle>(() => `/ideas/${ideaId}`);
  }

  /** PUT /ideas/{id} — manual edit of the 6 fields (RF-9); 409 while generating. */
  actualizar(ideaId: string, campos: IdeaFields): Promise<Idea> {
    return firstValueFrom(this.http.put<Idea>(`/ideas/${ideaId}`, campos));
  }

  /** POST /ideas/{id}/improve — request an AI improvement (RF-8, case 10). */
  solicitarMejora(ideaId: string, instruction: string): Promise<MejoraResultado> {
    return firstValueFrom(this.http.post<MejoraResultado>(`/ideas/${ideaId}/improve`, { instruction }));
  }

  /** POST /ideas/{id}/versions/{vid}/decide — accept/discard a pending version (RF-8/RF-13). */
  decidirVersion(ideaId: string, versionId: string, decision: 'accept' | 'discard'): Promise<Idea> {
    return firstValueFrom(this.http.post<Idea>(`/ideas/${ideaId}/versions/${versionId}/decide`, { decision }));
  }

  /** POST /ideas/{id}/request-publication — move to SOLICITANDO_PUBLICACION (RF-10). */
  solicitarPublicacion(ideaId: string): Promise<Idea> {
    return firstValueFrom(this.http.post<Idea>(`/ideas/${ideaId}/request-publication`, {}));
  }
}
