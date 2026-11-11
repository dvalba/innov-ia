import { Component, inject } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CatalogService } from '../../services/catalog.service';
import { DebatePanel } from '../../components/debate-panel/debate-panel';
import { errorMessage } from '../../../../shared/interceptors/error.interceptor';
import { Debate } from '../../../../shared/types/models';

/**
 * Read-only public debate (T-085, RF-24).
 *
 * The full thread of a published idea's debate, always in read-only mode
 * (no composer, no deadline adjustment): the target of the "Ver el debate
 * completo" link in the compact closure box of the detail page. The debate is
 * a read-only resource (`GET /catalog/{id}/debate`); the title comes from the
 * public detail resource so the header can identify the idea. The page hosts
 * the `debate-panel` with `soloLectura` (T-085) and a back link to the detail.
 */
@Component({
  selector: 'app-debate-readonly',
  imports: [RouterLink, DebatePanel],
  templateUrl: './debate-readonly.html',
})
export class DebateReadonly {
  private readonly catalogoService = inject(CatalogService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  /** The `:id` route parameter, read once for this lazy-loaded instance. */
  readonly ideaId = this.route.snapshot.paramMap.get('id') as string;

  /** `GET /catalog/{id}` — the title for the header (RF-23). */
  readonly detalle = this.catalogoService.detallePublico(this.ideaId);

  /** `GET /catalog/{id}/debate` — the full thread (RF-24). */
  readonly debate = this.catalogoService.debateDe(this.ideaId);

  /** The load error message (404 → "not in the catalog"), in Spanish (RNF-3). */
  protected mensajeError(): string {
    return errorMessage(this.debate.error() ?? undefined);
  }

  /** The idea title for the header (RNF-4); a placeholder while loading. */
  protected titulo(): string {
    return this.detalle.value()?.fields.title || 'Iniciativa';
  }

  /** The debate read state, or `null` while loading (the panel's input type). */
  protected debateValor(): Debate | null {
    return this.debate.value() ?? null;
  }

  /** Back to the public detail of this idea (RF-23). */
  protected irAlDetalle(): void {
    void this.router.navigate(['/catalogo/publico', this.ideaId]);
  }
}
