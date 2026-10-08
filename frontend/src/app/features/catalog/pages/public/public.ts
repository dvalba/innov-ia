import { Component, inject } from '@angular/core';
import { CatalogService } from '../../services/catalog.service';
import { CAMPOS_DEF, formatearDetalle, origenLabel } from '../../../../shared/utils/idea-fields';
import { formatearDia, formatearFecha } from '../../../../shared/utils/format';

/**
 * Public catalog (T-052, RF-20, RNF-7).
 *
 * Reads only (no edit actions at all, RNF-7): every `VALIDADA_PUBLICA` idea
 * the community has published — the 7 fields, the proponent's name and area
 * (never the contact), and the registration + publication dates. It is
 * reachable by any signed-in user (the route carries no role guard), so the
 * catalog lists ideas of any owner. The page only consumes the `catalog`
 * (G10) contract through `httpResource` (guideline §5).
 */
@Component({
  selector: 'app-public-catalog',
  templateUrl: './public.html',
})
export class PublicCatalog {
  private readonly catalog = inject(CatalogService);

  /** `GET /catalog/public` — the published ideas, newest first. */
  protected readonly catalogo = this.catalog.catalogo;

  protected readonly campos = CAMPOS_DEF;
  protected readonly formatearDetalle = formatearDetalle;
  protected readonly formatearDia = formatearDia;
  protected readonly formatearFecha = formatearFecha;
  protected readonly origenLabel = origenLabel;
}
