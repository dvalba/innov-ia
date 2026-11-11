import { Component, inject, signal } from '@angular/core';
import { CalibrationPanel } from '../../components/calibration-panel/calibration-panel';
import { ValidatePanel } from '../../components/validate-panel/validate-panel';
import { ValidationService } from '../../services/validation.service';
import { DecisionOutcome, QueueStage } from '../../../../shared/types/models';

/**
 * Specialist validation queue (T-051, RF-14/RF-15/RF-16; T-084, RF-14 v2.2).
 *
 * The two-stage review surface (RF-14 v2.2): the stage tabs switch the
 * service's `etapa` (the `cola` resource refires on `?stage=…`). The
 * publication stage validates or rejects each entry; the calibration stage
 * opens the full ficha (6 fields, compact debate, AI evaluation, final
 * decision) through `calibration-panel`. After any decision the queue
 * reloads (the entry leaves its state) and a Spanish confirmation is shown.
 * The queue only consumes the G10 contract; every rule (403/400/409/422) is
 * enforced by the backend and surfaced here (RNF-3/RNF-4).
 */
@Component({
  selector: 'app-review-queue',
  imports: [ValidatePanel, CalibrationPanel],
  templateUrl: './queue.html',
})
export class ReviewQueue {
  private readonly validation = inject(ValidationService);

  /** The active stage tab (mirrors the service's `etapa` signal). */
  protected readonly etapa = this.validation.etapa;
  /** `GET /validation/queue?stage=…` — the stage's ideas (RF-14 v2.2). */
  protected readonly cola = this.validation.cola;
  /** `true` while a decision is in flight in any panel. */
  protected readonly operando = signal(false);
  /** The Spanish confirmation shown after a decision (RNF-4). */
  protected readonly confirmacion = signal('');

  protected readonly ETAPAS: { valor: QueueStage; etiqueta: string }[] = [
    { valor: 'publicacion', etiqueta: 'Publicación' },
    { valor: 'calibracion', etiqueta: 'Calibración' },
  ];

  constructor() {
    // Refetch on every entry: the root-level resource keeps its cached queue
    // across sessions/users within the same SPA lifecycle.
    this.cola.reload();
  }

  /** Switches the stage tab (the resource refires through `etapa`). */
  protected cambiarEtapa(stage: QueueStage): void {
    this.confirmacion.set('');
    this.validation.cambiarEtapa(stage);
  }

  protected onComenzada(): void {
    this.confirmacion.set('');
    this.operando.set(true);
  }

  /** Unlocks after any mutation finished (success or failure). */
  protected onTerminada(): void {
    this.operando.set(false);
  }

  protected onDecididaPublicacion(resultado: 'validada' | 'rechazada'): void {
    this.confirmacion.set(
      resultado === 'validada'
        ? 'Idea validada: la iniciativa se publicó en el catálogo.'
        : 'Idea rechazada: la iniciativa volvió a «En desarrollo» con tu nota.',
    );
    this.cola.reload();
  }

  protected onDecididaCalibracion(outcome: DecisionOutcome): void {
    this.confirmacion.set(
      outcome === 'ACEPTADA'
        ? 'Decisión registrada: la iniciativa quedó en la zona de aceptadas del catálogo.'
        : outcome === 'ARCHIVADA'
          ? 'Decisión registrada: la iniciativa quedó en la zona de archivadas; el proponente podrá solicitar una reevaluación.'
          : 'Decisión registrada: la iniciativa quedó en la zona de rechazadas del catálogo.',
    );
    this.cola.reload();
  }

  protected cerrarConfirmacion(): void {
    this.confirmacion.set('');
  }
}
