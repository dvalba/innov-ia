import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { CatalogService } from '../../services/catalog.service';
import { IdeaCard } from '../../../../shared/components/idea-card/idea-card';
import { origenLabel } from '../../../../shared/utils/idea-fields';
import { formatearFecha } from '../../../../shared/utils/format';
import { IdeaCatalogo } from '../../../../shared/types/models';

/**
 * Public catalog (T-052, RF-20, RNF-7; T-056: shared `idea-card`; T-077).
 *
 * Reads only (no edit actions at all, RNF-7): every `VALIDADA_PUBLICA` idea
 * the community has published. It is reachable by any signed-in user (the
 * route carries no role guard), so the catalog lists ideas of any owner. Each
 * entry is the shared `idea-card` in its `compact` variant (title + one meta
 * line + arrow), wrapped in a `routerLink` to the detail view
 * (`/catalogo/publico/{id}`, RF-23); the page only consumes the `catalog`
 * (G10) contract through `httpResource` (guideline §5).
 */
@Component({
  selector: 'app-public-catalog',
  imports: [RouterLink, IdeaCard],
  templateUrl: './public.html',
})
export class PublicCatalog {
  private readonly catalog = inject(CatalogService);

  /** `GET /catalog/public` — the published ideas, newest first. */
  protected readonly catalogo = this.catalog.catalogo;

  protected readonly origenLabel = origenLabel;

  constructor() {
    // Refetch on every entry: the root-level resource keeps its cached list
    // across sessions/users within the same SPA lifecycle.
    this.catalogo.reload();
  }

  /** The catalog card meta line (publication date + origin). */
  protected meta(idea: IdeaCatalogo): string {
    return `Publicada el ${formatearFecha(idea.publishedAt)} · Origen ${origenLabel(idea.origin)}`;
  }
}
