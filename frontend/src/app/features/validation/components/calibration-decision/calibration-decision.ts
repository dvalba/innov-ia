import { Component, computed, effect, inject, input, output, signal } from '@angular/core';
import { ValidationService } from '../../services/validation.service';
import { BandScale } from '../../../../shared/components/band-scale/band-scale';
import { ConfirmDialog } from '../../../../shared/components/confirm-dialog/confirm-dialog';
import { errorMessage } from '../../../../shared/interceptors/error.interceptor';
import {
  BANDA_LABEL,
  bandaDe,
  promedioDe,
} from '../../../../shared/utils/decision';
import {
  CRITERIOS_EVALUACION,
  CRITERIO_LABEL,
  CriterioClave,
} from '../../../../shared/utils/evaluation';
import { DecisionOutcome, Evaluacion } from '../../../../shared/types/models';

/**
 * Final-decision form of the calibration stage (T-084, RF-27).
 *
 * Shows the idea's current final judgment (average + band, live) and lets the
 * specialist choose the outcome (pre-selected from the band, never forced),
 * write the reason (mandatory for ARCHIVADA/RECHAZADA) and confirm through a
 * consequence dialog (`POST /validation/{id}/decision`). A 409
 * `DECISION_MISMATCH` from the backend (the authority for the band) is
 * surfaced with its `score`/`band` details; a 400 for a missing reason is
 * surfaced as-is (RNF-3). `comenzada` fires before the mutation and
 * `terminada` in `finally` (success or failure) so the parent can unlock and
 * reload (RNF-2/RNF-3).
 */
@Component({
  selector: 'app-calibration-decision',
  imports: [BandScale, ConfirmDialog],
  templateUrl: './calibration-decision.html',
})
export class CalibrationDecision {
  /** The id of the idea being decided. */
  readonly ideaId = input.required<string>();
  /** The current final judgment (`evaluation`); drives the live average/band. */
  readonly evaluation = input<Evaluacion | null>(null);
  /** `true` while the parent processes a decision (locks every panel). */
  readonly ocupado = input(false);
  /** A mutation started, so the parent can lock the other panels. */
  readonly comenzada = output<void>();
  /** A mutation finished (success or failure) so the parent can reload. */
  readonly terminada = output<void>();
  /** The decision was recorded (success only) so the parent can confirm. */
  readonly decidida = output<DecisionOutcome>();

  private readonly validation = inject(ValidationService);

  /** The outcome the specialist chose (`null` = follow the band). */
  protected readonly resultado = signal<DecisionOutcome | null>(null);
  /** The reason (mandatory for ARCHIVADA/RECHAZADA, optional for ACEPTADA). */
  protected readonly motivo = signal('');
  /** `true` while the confirmation dialog is open. */
  protected readonly confirmando = signal(false);
  /** `true` while the decision call is in flight. */
  protected readonly enviando = signal(false);
  /** The last backend error message to surface (RNF-3). */
  protected readonly error = signal('');
  /** The 409 `score`/`band` details, when the outcome did not match the band. */
  protected readonly detallesBanda = signal<{ score: number; band: DecisionOutcome } | null>(null);

  protected readonly BANDA_LABEL = BANDA_LABEL;
  protected readonly opciones: { valor: DecisionOutcome; descripcion: string }[] = [
    {
      valor: 'ACEPTADA',
      descripcion: 'La iniciativa queda en la zona de aceptadas del catálogo.',
    },
    {
      valor: 'ARCHIVADA',
      descripcion: 'La iniciativa queda en la zona de archivadas y el proponente podrá solicitar una reevaluación.',
    },
    {
      valor: 'RECHAZADA',
      descripcion: 'La iniciativa queda en la zona de rechazadas y el proponente verá tu motivo.',
    },
  ];

  /** The criteria of the current judgment in canonical order. */
  protected readonly criteriosVigentes = computed(() => {
    const ev = this.evaluation();
    const porClave = new Map((ev?.criteria ?? []).map((c) => [c.criterion, c]));
    return CRITERIOS_EVALUACION.map((def) => porClave.get(def.clave)).filter(
      (c): c is NonNullable<typeof c> => c !== undefined,
    );
  });

  /** The average of the current judgment (null when it has no criteria). */
  protected readonly promedioActual = computed(() =>
    promedioDe(this.criteriosVigentes().map((c) => c.score)),
  );

  /** The band the current average falls into (null without criteria). */
  protected readonly bandaActual = computed(() => {
    const p = this.promedioActual();
    return p == null ? null : bandaDe(p);
  });

  /** The effective outcome: the chosen one, or the band when not chosen yet. */
  protected readonly efectivo = computed<DecisionOutcome>(
    () => this.resultado() ?? this.bandaActual() ?? 'ACEPTADA',
  );

  /** `true` when the effective outcome is the band of the current average. */
  protected readonly coincideConBanda = computed(
    () => this.bandaActual() == null || this.efectivo() === this.bandaActual(),
  );

  /** The reason is mandatory for ARCHIVADA/RECHAZADA (400 on the backend). */
  protected readonly motivoObligatorio = computed(() => this.efectivo() !== 'ACEPTADA');

  /** `true` when the form may be confirmed (reason rule satisfied). */
  protected readonly puedeConfirmar = computed(
    () => !this.motivoObligatorio() || this.motivo().trim() !== '',
  );

  /** The consequence warning of the confirmation dialog (per outcome). */
  protected readonly mensajeConfirmacion = computed(() => {
    switch (this.efectivo()) {
      case 'ACEPTADA':
        return 'Vas a marcar la iniciativa como Aceptada: quedará en la zona de aceptadas del catálogo. Esta decisión es definitiva: la iniciativa no volverá a evaluarse.';
      case 'ARCHIVADA':
        return 'Vas a marcar la iniciativa como Archivada: quedará en la zona de archivadas del catálogo y el proponente podrá solicitar una reevaluación.';
      case 'RECHAZADA':
        return 'Vas a marcar la iniciativa como Rechazada: quedará en la zona de rechazadas del catálogo y el proponente verá el motivo que escribiste. Esta decisión es definitiva: la iniciativa no volverá a evaluarse.';
    }
  });

  /** `true` to render the confirm button in the danger color. */
  protected readonly peligro = computed(() => this.efectivo() === 'RECHAZADA');

  constructor() {
    // When the judgment reloads (accept/replace), the choice and the error
    // state are reset so the form follows the new band again.
    let anterior: Evaluacion | null | undefined;
    effect(() => {
      const ev = this.evaluation();
      if (ev === anterior) return;
      anterior = ev;
      this.resultado.set(null);
      this.motivo.set('');
      this.error.set('');
      this.detallesBanda.set(null);
      this.confirmando.set(false);
    });
  }

  protected setResultado(valor: DecisionOutcome): void {
    this.resultado.set(valor);
    this.error.set('');
    this.detallesBanda.set(null);
  }

  protected setMotivo(raw: string): void {
    this.motivo.set(raw);
  }

  /** Spanish label of a criterion key (RNF-4). */
  protected etiquetaCriterio(clave: string): string {
    return CRITERIO_LABEL[clave as CriterioClave] ?? clave;
  }

  /** The width (0-100%) of a score volume bar. */
  protected anchoBar(score: number): number {
    return Math.min(Math.max(score, 0), 10) * 10;
  }

  protected abrirConfirmacion(): void {
    if (!this.puedeConfirmar()) return;
    this.confirmando.set(true);
  }

  protected cerrarConfirmacion(): void {
    this.confirmando.set(false);
  }

  /** Sends the confirmed decision (RF-27). */
  protected confirmar(): void {
    this.enviando.set(true);
    this.error.set('');
    this.detallesBanda.set(null);
    this.comenzada.emit();
    const outcome = this.efectivo();
    const reason = this.motivoObligatorio() ? this.motivo().trim() : null;
    void this.validation
      .decidir(this.ideaId(), outcome, reason)
      .then(() => {
        this.confirmando.set(false);
        this.decidida.emit(outcome);
      })
      .catch((err) => {
        this.error.set(errorMessage(err));
        const body = (err as { error?: { code?: string; details?: Record<string, unknown> } })
          ?.error;
        if (body?.code === 'DECISION_MISMATCH') {
          const score = body.details?.['score'];
          const band = body.details?.['band'];
          if (typeof score === 'number' && typeof band === 'string') {
            this.detallesBanda.set({ score, band: band as DecisionOutcome });
          }
        }
      })
      .finally(() => {
        this.enviando.set(false);
        this.terminada.emit();
      });
  }

  protected descartarError(): void {
    this.error.set('');
    this.detallesBanda.set(null);
  }
}
