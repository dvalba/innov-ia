import { Component, computed, inject } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { CatalogService } from '../../services/catalog.service';
import { formatearFecha } from '../../../../shared/utils/format';
import {
  CATALOG_ZONES,
  CatalogZone,
  ItemZona,
  ZONA_LABEL,
} from '../../../../shared/types/models';

/**
 * Public catalog (T-052, RF-20, RNF-7; T-085: four zones).
 *
 * Read-only (RNF-7): the catalog of every published idea organized in the four
 * zones of RF-20 (En proceso / Aceptadas / Rechazadas / Archivadas), each a
 * projection of one idea state (D21). The active tab is the `?zone=` query
 * parameter (deep-linkable, RNF-6): it defaults to `en-proceso` and is kept in
 * sync with the URL so a shared zone link lands on the right tab. Each entry is
 * a compact row (title + one meta line + description) wrapped in a `routerLink`
 * to the detail view (`/catalogo/publico/{id}`, RF-23). The page only consumes
 * the `catalog` (G10) contract through a single `httpResource` that returns all
 * four zones (guideline §5), so switching tabs never refetches.
 */
@Component({
  selector: 'app-public-catalog',
  imports: [RouterLink],
  templateUrl: './public.html',
})
export class PublicCatalog {
  private readonly catalog = inject(CatalogService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  /** `GET /catalog/public` — the four zones (RF-20). */
  protected readonly catalogo = this.catalog.catalogoZonas;

  /** The `?zone=` query value as a signal (deep-link, RNF-6). */
  private readonly zonaQuery = toSignal(this.route.queryParamMap, {
    requireSync: true,
  });

  /** The four zones in canonical order (the tab order, D21). */
  protected readonly zonas = CATALOG_ZONES;

  /** Spanish label of a zone (RNF-4). */
  protected readonly zonaLabel = ZONA_LABEL;

  /** The active zone: the valid `?zone=` value or `en-proceso` by default. */
  protected readonly zonaActiva = computed<CatalogZone>(() => {
    const q = this.zonaQuery().get('zone');
    return (CATALOG_ZONES as readonly string[]).includes(q ?? '')
      ? (q as CatalogZone)
      : 'en-proceso';
  });

  constructor() {
    // Refetch on every entry: the root-level resource keeps its cached zones
    // across sessions/users within the same SPA lifecycle.
    this.catalogo.reload();
  }

  /** The items of the currently active zone. */
  protected items(): ItemZona[] {
    const zonas = this.catalogo.value()?.zones;
    return zonas ? zonas[this.zonaActiva()] ?? [] : [];
  }

  /** The count of items in a zone (the tab badge). */
  protected totalDe(zona: CatalogZone): number {
    const zonas = this.catalogo.value()?.zones;
    return zonas ? zonas[zona]?.length ?? 0 : 0;
  }

  /** The compact row meta line (publication date). */
  protected meta(item: ItemZona): string {
    return `Publicada el ${formatearFecha(item.publishedAt)}`;
  }

  /** Switches the active tab and keeps the `?zone=` query in sync (RNF-6). */
  protected cambiarZona(zona: CatalogZone): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { zone: zona },
      queryParamsHandling: 'merge',
    });
  }
}
