import { Component, inject, input, output, signal } from '@angular/core';
import { MyIdeasService } from '../../services/my-ideas.service';
import {
  CAMPOS_DEF,
  formatearDetalle,
  versionOrigenLabel,
} from '../../services/my-idea-fields';
import { errorMessage } from '../../../../shared/interceptors/error.interceptor';
import { formatearDia } from '../../../../shared/utils/format';
import { IdeaVersion, SolicitudMejora } from '../../../../shared/types/models';

/** A version decision (accept / discard) delegated to the parent. */
export interface DecisionVersion {
  version: IdeaVersion;
  decision: 'accept' | 'discard';
}

/**
 * Request-an-AI-improvement panel (T-048, RF-8, case 10).
 *
 * Collects the improvement instruction and sends `POST /ideas/{id}/improve`.
 * With the IA available the outcome is a new pending version; without it the
 * request is registered (case 10 notice) and shown as an informational callout.
 * Below, the pending versions are listed with their proposed fields and a
 * single Aceptar/Descartar decision each. Version decisions are delegated to
 * the parent (it owns the idea resource and reloads it). UI copy in Spanish.
 */
@Component({
  selector: 'app-improve-panel',
  templateUrl: './improve-panel.html',
})
export class ImprovePanel {
  /** The id of the idea the versions belong to. */
  readonly ideaId = input.required<string>();
  /** The pending versions to decide on. */
  readonly versiones = input.required<IdeaVersion[]>();
  /** `true` while the parent is processing a version decision. */
  readonly ocupado = input(false);
  /** A version was decided (accepted or discarded). */
  readonly decision = output<DecisionVersion>();
  /** An improvement round finished (either outcome) so the parent can reload. */
  readonly mejorado = output<void>();

  private readonly ideas = inject(MyIdeasService);

  protected readonly instruccion = signal('');
  /** `true` while an improve call is in flight. */
  protected readonly enviando = signal(false);
  protected readonly error = signal('');
  /** The case-10 notice (IA unavailable) from the last improve, when any. */
  protected readonly aviso = signal('');
  /** A case-10 request registered by the last improve (if any). */
  protected readonly solicitudRegistrada = signal<SolicitudMejora | null>(null);
  protected readonly formatearDia = formatearDia;
  protected readonly campos = CAMPOS_DEF;
  protected readonly formatearDetalle = formatearDetalle;
  protected readonly versionOrigenLabel = versionOrigenLabel;

  protected solicitar(): void {
    const texto = this.instruccion().trim();
    if (!texto) return;
    this.enviando.set(true);
    this.error.set('');
    this.aviso.set('');
    this.ideas
      .solicitarMejora(this.ideaId(), texto)
      .then((res) => {
        if ('notice' in res) {
          this.aviso.set(res.notice);
          this.solicitudRegistrada.set(res.improvementRequest);
        }
        this.instruccion.set('');
        this.mejorado.emit();
      })
      .catch((err) => this.error.set(errorMessage(err)))
      .finally(() => this.enviando.set(false));
  }

  protected decidir(v: IdeaVersion, decision: 'accept' | 'discard'): void {
    this.decision.emit({ version: v, decision });
  }

  protected limpiarAviso(): void {
    this.aviso.set('');
  }

  protected limpiarError(): void {
    this.error.set('');
  }
}
