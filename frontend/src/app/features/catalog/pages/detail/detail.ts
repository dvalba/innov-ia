import { Component, computed, inject } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CatalogService } from '../../services/catalog.service';
import { BadgeState } from '../../../../shared/components/badge-state/badge-state';
import { IdeaCard } from '../../../../shared/components/idea-card/idea-card';
import { DebatePanel } from '../../components/debate-panel/debate-panel';
import { EvaluationPanel } from '../../components/evaluation-panel/evaluation-panel';
import { SessionService } from '../../../../shared/services/session.service';
import { errorMessage } from '../../../../shared/interceptors/error.interceptor';
import { formatearDia, formatearFecha } from '../../../../shared/utils/format';
import { origenLabel } from '../../../../shared/utils/idea-fields';
import { resultadoLabel } from '../../../../shared/utils/decision';
import { ROLE_VALIDATOR } from '../../../../shared/types/models';

/**
 * Public catalog detail (T-077, RF-23).
 *
 * The read-only detail of one `VALIDADA_PUBLICA` idea: the 6 fields (the
 * proponent reduced to name/area, never the contact, RNF-7) in the shared
 * `idea-card` (`full` variant), the public debate (`debate-panel`, RF-24/RF-25)
 * and the final evaluation + the immutable AI snapshot (`evaluation-panel`,
 * RF-26). The two `httpResource`s are built for the `:id` read once from the
 * lazy-loaded route (guideline §5); a panel that mutates its resource tells the
 * parent to reload so the server stays the source of truth (RNF-2). The page
 * has no editing of its own — the idea is never modified in the catalog (D12) —
 * and the panel availability follows the session's roles.
 */
@Component({
  selector: 'app-catalog-detail',
  imports: [RouterLink, IdeaCard, BadgeState, DebatePanel, EvaluationPanel],
  templateUrl: './detail.html',
})
export class CatalogDetail {
  private readonly catalogoService = inject(CatalogService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly session = inject(SessionService);

  /** The `:id` route parameter, read once for this lazy-loaded instance. */
  readonly ideaId = this.route.snapshot.paramMap.get('id') as string;

  /** `GET /catalog/{id}` — the 6 fields + the two evaluations (RF-23). */
  readonly detalle = this.catalogoService.detallePublico(this.ideaId);

  /** `GET /catalog/{id}/debate` — the public debate (RF-24). */
  readonly debate = this.catalogoService.debateDe(this.ideaId);

  /** `true` for a specialist (may accept/replace the evaluation, RF-26). */
  protected readonly especialista = computed(() => this.session.tieneRol(ROLE_VALIDATOR));

  protected readonly origenLabel = origenLabel;
  protected readonly formatearFecha = formatearFecha;
  protected readonly formatearDia = formatearDia;
  protected readonly resultadoLabel = resultadoLabel;

  /** The full-variant meta lines (registration + publication, origin). */
  protected meta(): string[] {
    const idea = this.detalle.value();
    if (!idea) return [];
    return [
      `Registrada el ${formatearDia(idea.createdAt)} · Publicada el ${formatearFecha(idea.publishedAt)} · Origen ${origenLabel(idea.origin)}`,
    ];
  }

  /** The load error message (404 → "not in the catalog"), in Spanish (RNF-3). */
  protected mensajeError(): string {
    return errorMessage(this.detalle.error() ?? undefined);
  }

  /** The recorded decision score, with its 2-decimal display (RF-27). */
  protected scoreDecision(): string {
    const d = this.detalle.value()?.decision;
    return d ? d.score.toFixed(2) : '';
  }

  /** A panel finished a mutation: reload both reactive resources (RNF-2). */
  protected refresh(): void {
    this.detalle.reload();
    this.debate.reload();
  }

  protected irAlCatalogo(): void {
    void this.router.navigate(['/catalogo']);
  }
}
