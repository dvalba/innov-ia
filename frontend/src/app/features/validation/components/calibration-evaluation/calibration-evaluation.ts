import { Component, computed, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ValidationService } from '../../services/validation.service';
import { BandScale } from '../../../../shared/components/band-scale/band-scale';
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
  evaluacionEstadoLabel,
} from '../../../../shared/utils/evaluation';
import { formatearFecha } from '../../../../shared/utils/format';
import { CriterioEvaluacion, Evaluacion } from '../../../../shared/types/models';

/** One editable row of the replacement form (the 5 fixed criteria, RF-26). */
interface CriterioForm {
  clave: CriterioClave;
  etiqueta: string;
  score: number;
  justification: string;
}

/** Score bounds (RF-26: integer 1-10 per criterion); mirror of the backend. */
const SCORE_MIN = 1;
const SCORE_MAX = 10;

/**
 * Calibration evaluation panel (T-084, RF-26/RF-27).
 *
 * Shows the idea's current final judgment (the 5 criteria, the band scale
 * with its live average) in the calibration stage and offers the two
 * specialist actions: accept the AI evaluation
 * (`POST /validation/{id}/evaluation/accept`) or replace it with the
 * specialist's own judgment over the 5 criteria
 * (`POST /validation/{id}/evaluation`). While the replacement form is filled,
 * the draft average and its band preview live (the backend thresholds are the
 * authority; a mismatch 409s). `comenzada` fires before the mutation and
 * `terminada` in `finally` (success or failure) so the parent can unlock and
 * reload (RNF-2/RNF-3).
 */
@Component({
  selector: 'app-calibration-evaluation',
  imports: [BandScale, FormsModule],
  templateUrl: './calibration-evaluation.html',
})
export class CalibrationEvaluation {
  /** The id of the idea whose evaluation is shown. */
  readonly ideaId = input.required<string>();
  /** The current final judgment (`evaluation`). */
  readonly evaluation = input<Evaluacion | null>(null);
  /** The immutable AI snapshot (`aiEvaluation`). */
  readonly aiEvaluation = input<Evaluacion | null>(null);
  /** `true` while the parent processes a decision (locks every panel). */
  readonly ocupado = input(false);
  /** A mutation started, so the parent can lock the other panels. */
  readonly comenzada = output<void>();
  /** A mutation finished (success or failure) so the parent can reload. */
  readonly terminada = output<void>();

  private readonly validation = inject(ValidationService);

  /** `true` while the accept call is in flight. */
  protected readonly aceptando = signal(false);
  /** `true` while the replacement form is revealed. */
  protected readonly sustituyendo = signal(false);
  /** `true` while the replacement call is in flight. */
  protected readonly guardando = signal(false);
  /** The last backend error message to surface (RNF-3). */
  protected readonly error = signal('');
  /** The 422 `details.problems` list (RNF-5) when a replacement was invalid. */
  protected readonly problemas = signal<string[]>([]);
  /** The editable replacement criteria (the 5 fixed, in canonical order). */
  protected readonly criterios = signal<CriterioForm[]>([]);

  protected readonly evaluacionEstadoLabel = evaluacionEstadoLabel;
  protected readonly BANDA_LABEL = BANDA_LABEL;
  protected readonly formatearFecha = formatearFecha;

  /** The current screen state: the lifecycle state, or none while open. */
  protected estado(): string {
    return this.evaluation()?.status ?? 'SIN_EVALUACION';
  }

  /** The criteria of the current judgment in canonical order. */
  protected readonly criteriosVigentes = computed(() => {
    const ev = this.evaluation();
    const porClave = new Map((ev?.criteria ?? []).map((c) => [c.criterion, c]));
    return CRITERIOS_EVALUACION.map((def) => porClave.get(def.clave)).filter(
      (c): c is CriterioEvaluacion => c !== undefined,
    );
  });

  /** The average of the current judgment (null when it has no criteria). */
  protected readonly promedioActual = computed(() =>
    promedioDe(this.criteriosVigentes().map((c) => c.score)),
  );

  /**
   * The draft average of the replacement form: only computed once all 5 rows
   * carry an integer score 1-10 (the live preview, RNF-4).
   */
  protected readonly promedioBorrador = computed(() => {
    const filas = this.criterios();
    if (
      filas.length !== CRITERIOS_EVALUACION.length ||
      !filas.every(
        (f) => Number.isInteger(f.score) && f.score >= SCORE_MIN && f.score <= SCORE_MAX,
      )
    ) {
      return null;
    }
    return promedioDe(filas.map((f) => f.score));
  });

  /** The band of the draft average (null until it is complete). */
  protected readonly bandaBorrador = computed(() => {
    const p = this.promedioBorrador();
    return p == null ? null : bandaDe(p);
  });

  /** Spanish label of a criterion key (RNF-4). */
  protected etiquetaCriterio(clave: string): string {
    return CRITERIO_LABEL[clave as CriterioClave] ?? clave;
  }

  /** The width (0-100%) of a score volume bar. */
  protected anchoBar(score: number): number {
    return Math.min(Math.max(score, 0), SCORE_MAX) * 10;
  }

  private nuevoFormulario(): CriterioForm[] {
    const ai = this.aiEvaluation()?.criteria ?? [];
    const porClave = new Map(ai.map((c) => [c.criterion, c]));
    return CRITERIOS_EVALUACION.map((def) => {
      const src = porClave.get(def.clave);
      return {
        clave: def.clave,
        etiqueta: def.etiqueta,
        score: src?.score ?? 0,
        justification: src?.justification ?? '',
      };
    });
  }

  protected setScore(index: number, raw: string): void {
    const num = raw === '' ? 0 : Number(raw);
    const score = Number.isNaN(num) ? 0 : Math.trunc(num);
    this.criterios.set(this.criterios().map((c, i) => (i === index ? { ...c, score } : c)));
  }

  protected setJustificacion(index: number, raw: string): void {
    this.criterios.set(
      this.criterios().map((c, i) => (i === index ? { ...c, justification: raw } : c)),
    );
  }

  /** `true` when all 5 rows carry a score 1-10 and a non-empty justification. */
  protected formularioValido(): boolean {
    return this.criterios().every(
      (c) =>
        Number.isInteger(c.score) &&
        c.score >= SCORE_MIN &&
        c.score <= SCORE_MAX &&
        c.justification.trim() !== '',
    );
  }

  protected mostrarSustitucion(): void {
    this.criterios.set(this.nuevoFormulario());
    this.sustituyendo.set(true);
    this.error.set('');
    this.problemas.set([]);
  }

  protected descartarSustitucion(): void {
    this.sustituyendo.set(false);
    this.error.set('');
    this.problemas.set([]);
  }

  /** Accepts the AI evaluation as the final judgment (status `ACEPTADA`). */
  protected aceptar(): void {
    this.aceptando.set(true);
    this.error.set('');
    this.comenzada.emit();
    void this.validation
      .aceptarEvaluacion(this.ideaId())
      .catch((err) => this.error.set(errorMessage(err)))
      .finally(() => {
        this.aceptando.set(false);
        this.terminada.emit();
      });
  }

  /** Replaces the final judgment with the specialist's own (status `SUSTITUIDA`). */
  protected sustituir(): void {
    if (!this.formularioValido()) return;
    this.guardando.set(true);
    this.error.set('');
    this.problemas.set([]);
    this.comenzada.emit();
    const criteria = this.criterios().map((c) => ({
      criterion: c.clave,
      score: c.score,
      justification: c.justification.trim(),
    }));
    void this.validation
      .sustituirEvaluacion(this.ideaId(), criteria)
      .then(() => this.sustituyendo.set(false))
      .catch((err) => {
        this.error.set(errorMessage(err));
        const details = (err as { error?: { details?: Record<string, unknown> } })?.error
          ?.details;
        const problems = details?.['problems'];
        if (Array.isArray(problems)) this.problemas.set(problems.map(String));
      })
      .finally(() => {
        this.guardando.set(false);
        this.terminada.emit();
      });
  }

  protected descartarError(): void {
    this.error.set('');
    this.problemas.set([]);
  }
}
