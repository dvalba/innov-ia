import { Component, inject, signal } from '@angular/core';
import { ValidatePanel } from '../../components/validate-panel/validate-panel';
import { ValidationService } from '../../services/validation.service';

/**
 * Specialist validation queue (T-051, RF-14/RF-15/RF-16).
 *
 * Lists the ideas in `SOLICITANDO_PUBLICACION` (the `GET /validation/queue`
 * resource, oldest first) and lets the specialist validate or reject each one
 * through `validate-panel`. After a decision the queue reloads (the entry
 * leaves `SOLICITANDO_PUBLICACION`) and a Spanish confirmation is shown. The
 * queue only consumes the G10 contract; every rule (403/400/409) is enforced
 * by the backend and surfaced here (RNF-3/RNF).
 */
@Component({
  selector: 'app-review-queue',
  imports: [ValidatePanel],
  templateUrl: './queue.html',
})
export class ReviewQueue {
  private readonly validation = inject(ValidationService);

  /** `GET /validation/queue` — the SOLICITANDO_PUBLICACION ideas. */
  protected readonly cola = this.validation.cola;
  /** `true` while a decision is in flight in any panel. */
  protected readonly operando = signal(false);
  /** The Spanish confirmation shown after a decision (RNF-4). */
  protected readonly confirmacion = signal('');

  protected onComenzada(): void {
    this.confirmacion.set('');
    this.operando.set(true);
  }

  protected onDecidida(resultado: 'validada' | 'rechazada'): void {
    this.operando.set(false);
    this.confirmacion.set(
      resultado === 'validada'
        ? 'Idea validada: la iniciativa se publicó en el catálogo.'
        : 'Idea rechazada: la iniciativa volvió a «En desarrollo» con tu nota.',
    );
    this.cola.reload();
  }

  protected cerrarConfirmacion(): void {
    this.confirmacion.set('');
  }
}
