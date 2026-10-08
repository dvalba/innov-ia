import { httpResource } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { IdeaCatalogo } from '../../../shared/types/models';

/**
 * Public catalog API client (T-052, RF-20, RNF-7).
 *
 * A pure read side: the public catalog (`GET /catalog/public`) is exposed only
 * while an active session exists (any role), so it is the sole `httpResource`
 * of this feature. There are no mutations: the catalog is read-only and never
 * exposes proponent contact data (backend-reduced to name/area). The backend
 * is the source of truth (RNF-2); this client only consumes the `ideas` (G10)
 * contract.
 */
@Injectable({ providedIn: 'root' })
export class CatalogService {
  /** GET /catalog/public — the VALIDADA_PUBLICA ideas, newest first. */
  readonly catalogo = httpResource<IdeaCatalogo[]>(() => '/catalog/public');
}
