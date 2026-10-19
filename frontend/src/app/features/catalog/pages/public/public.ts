import { Component, inject } from '@angular/core';
import { CatalogService } from '../../services/catalog.service';
import { IdeaCard } from '../../../../shared/components/idea-card/idea-card';
import { origenLabel } from '../../../../shared/utils/idea-fields';
import { formatearDia, formatearFecha } from '../../../../shared/utils/format';
import { IdeaCatalogo } from '../../../../shared/types/models';

/**
 * Public catalog (T-052, RF-20, RNF-7; T-056: shared `idea-card`).
 *
 * Reads only (no edit actions at all, RNF-7): every `VALIDADA_PUBLICA` idea
 * the community has published — the 6 fields, the proponent's name and area
 * (never the contact), and the registration + publication dates. It is
 * reachable by any signed-in user (the route carries no role guard), so the
 * catalog lists ideas of any owner. Each entry is the shared `idea-card` in
 * its `full` variant (read-only) and the page only consumes the `catalog`
 * (G10) contract through `httpResource` (guideline §5).
 */
@Component({
  selector: 'app-public-catalog',
  imports: [IdeaCard],
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

  /** The catalog card meta line (publication + registration dates, origin). */
  protected meta(idea: IdeaCatalogo): string[] {
    return [
      `Publicada el ${formatearFecha(idea.publishedAt)} · Registrada el ${formatearDia(idea.createdAt)} · Origen ${origenLabel(idea.origin)}`,
    ];
  }
}
