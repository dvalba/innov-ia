import { Component, inject, input, output, signal } from '@angular/core';
import { ValidationService } from '../../services/validation.service';
import { IdeaCard } from '../../../../shared/components/idea-card/idea-card';
import { origenLabel } from '../../../../shared/utils/idea-fields';
import { errorMessage } from '../../../../shared/interceptors/error.interceptor';
import { formatearFecha } from '../../../../shared/utils/format';
import { IdeaCola } from '../../../../shared/types/models';

/** The two specialist outcomes (drives the parent's Spanish confirmation). */
export type ResultadoValidacion = 'validada' | 'rechazada';

/**
 * Specialist review panel (T-051, RF-14/RF-15/RF-16, case 13).
 *
 * Renders one review-queue entry — the 6 fields (the proponent reduced to
 * name/area, never the contact, RF-14) plus the origin and the request date —
 * and the two specialist decisions. "Validar" approves (publishes) the idea;
 * "Rechazar" reveals a mandatory expert comment (the button stays blocked
 * while it is empty, and the backend keeps its 400 on a blank comment, case
 * 13). The panel performs the mutated call and emits the outcome so the
 * parent reloads the queue and shows the Spanish confirmation (RNF-3/RNF-4).
 */
@Component({
  selector: 'app-validate-panel',
  imports: [IdeaCard],
  templateUrl: './validate-panel.html',
})
export class ValidatePanel {
  /** The queue entry being reviewed. */
  readonly entrada = input.required<IdeaCola>();
  /** `true` while the parent processes a decision (locks every panel). */
  readonly ocupado = input(false);
  /** A decision started, so the parent can lock the other panels. */
  readonly comenzada = output<void>();
  /** A decision finished so the parent can reload and confirm. */
  readonly decidida = output<ResultadoValidacion>();

  private readonly validation = inject(ValidationService);

  /** The expert rejection comment (mandatory to reject, case 13). */
  protected readonly comentario = signal('');
  /** `true` after "Rechazar" was pressed, to reveal the comment editor. */
  protected readonly rechazando = signal(false);
  /** `true` while this panel's own decision is in flight. */
  protected readonly enviando = signal(false);
  /** The last backend error message to surface (RNF-3). */
  protected readonly error = signal('');

  /** The queue-entry meta line (request date + origin, pre-formatted). */
  protected metaLinea(): string {
    const e = this.entrada();
    return `Solicitada el ${formatearFecha(e.requestDate)} · Origen ${origenLabel(e.origin)}`;
  }

  protected readonly formatearFecha = formatearFecha;
  protected readonly origenLabel = origenLabel;

  protected activarRechazo(): void {
    this.rechazando.set(true);
    this.error.set('');
  }

  protected cancelarRechazo(): void {
    this.rechazando.set(false);
    this.comentario.set('');
    this.error.set('');
  }

  protected onValidar(): void {
    void this.mutar(() => this.validation.aprobar(this.entrada().id), 'validada');
  }

  protected onRechazar(): void {
    const texto = this.comentario().trim();
    if (!texto) return;
    void this.mutar(() => this.validation.rechazar(this.entrada().id, texto), 'rechazada');
  }

  protected descartarError(): void {
    this.error.set('');
  }

  private async mutar(f: () => Promise<unknown>, resultado: ResultadoValidacion): Promise<void> {
    this.enviando.set(true);
    this.error.set('');
    this.comenzada.emit();
    try {
      await f();
      this.comentario.set('');
      this.rechazando.set(false);
      this.decidida.emit(resultado);
    } catch (err) {
      this.error.set(errorMessage(err));
    } finally {
      this.enviando.set(false);
    }
  }
}
