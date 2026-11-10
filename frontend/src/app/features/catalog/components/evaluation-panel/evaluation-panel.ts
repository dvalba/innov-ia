import { Component, inject, input, output, signal } from '@angular/core';
import { CatalogService } from '../../services/catalog.service';
import { errorMessage } from '../../../../shared/interceptors/error.interceptor';
import { formatearFecha } from '../../../../shared/utils/format';
import {
  CRITERIOS_EVALUACION,
  CRITERIO_LABEL,
  CriterioClave,
  evaluacionEstadoLabel,
} from '../../../../shared/utils/evaluation';
import { CriterioEvaluacion, Evaluacion, EvaluacionEstado } from '../../../../shared/types/models';

/** One editable row of the replacement form (the 5 fixed criteria, RF-26). */
interface CriterioForm {
  clave: CriterioClave;
  etiqueta: string;
  score: number;
  justification: string;
}

/** The screen state of the evaluation (the lifecycle state, or none yet). */
type EstadoPantalla = 'SIN_EVALUACION' | EvaluacionEstado;

// Score bounds (RF-26: integer 1-10 per criterion); mirror of the backend contract.
const SCORE_MIN = 1;
const SCORE_MAX = 10;

/**
 * Final-evaluation panel of the public detail (T-077, RF-26, cases 22-23).
 *
 * Renders the idea's final judgment (`evaluation`) and, once a decision has
 * been taken, the immutable AI snapshot (`aiEvaluation`). The read state is
 * passed in from the parent's reactive resource; the two specialist decisions
 * (`POST .../evaluation/accept`, `POST .../evaluation`) are performed through
 * `CatalogService` (guideline §5: mutations never use `httpResource`) and emit
 * `actualizada` so the parent reloads and the server stays the source of truth
 * (RNF-2). The evaluation is generated at the debate's closure (RF-26): before
 * that (or while the assistant is down) it is `null`/`PENDING` and the panel
 * only says so — the specialist may still replace it with their own judgment
 * (case 22/23), and the 422 problems come back as a readable list (RNF-5).
 */
@Component({
  selector: 'app-evaluation-panel',
  templateUrl: './evaluation-panel.html',
})
export class EvaluationPanel {
  /** The id of the idea whose evaluation is shown. */
  readonly ideaId = input.required<string>();
  /** The current final judgment (`evaluation`). */
  readonly evaluation = input<Evaluacion | null>(null);
  /** The immutable AI snapshot (`aiEvaluation`). */
  readonly aiEvaluation = input<Evaluacion | null>(null);
  /** `true` for a specialist (may accept/replace the evaluation, RF-26). */
  readonly especialista = input(false);
  /** A decision finished (accept / replace) so the parent can reload. */
  readonly actualizada = output<void>();

  private readonly catalogo = inject(CatalogService);

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

  protected readonly formatearFecha = formatearFecha;
  protected readonly evaluacionEstadoLabel = evaluacionEstadoLabel;

  /** The current screen state: the lifecycle state, or none while open. */
  protected estado(): EstadoPantalla {
    return this.evaluation()?.status ?? 'SIN_EVALUACION';
  }

  /** Spanish label of a criterion key (RNF-4). */
  protected etiquetaCriterio(clave: string): string {
    return CRITERIO_LABEL[clave as CriterioClave] ?? clave;
  }

  /** The criteria of an evaluation in canonical order (for display). */
  protected criteriosOrdenados(ev: Evaluacion | null): CriterioEvaluacion[] {
    const porClave = new Map((ev?.criteria ?? []).map((c) => [c.criterion, c]));
    return CRITERIOS_EVALUACION.map((def) => porClave.get(def.clave)).filter(
      (c): c is CriterioEvaluacion => c !== undefined,
    );
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
    this.criterios.set(
      this.criterios().map((c, i) => (i === index ? { ...c, score } : c)),
    );
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

  protected aceptar(): void {
    this.aceptando.set(true);
    this.error.set('');
    void this.catalogo
      .aceptarEvaluacion(this.ideaId())
      .then(() => this.actualizada.emit())
      .catch((err) => this.error.set(errorMessage(err)))
      .finally(() => this.aceptando.set(false));
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

  protected sustituir(): void {
    if (!this.formularioValido()) return;
    this.guardando.set(true);
    this.error.set('');
    this.problemas.set([]);
    const criteria = this.criterios().map((c) => ({
      criterion: c.clave,
      score: c.score,
      justification: c.justification.trim(),
    }));
    void this.catalogo
      .sustituirEvaluacion(this.ideaId(), criteria)
      .then(() => {
        this.sustituyendo.set(false);
        this.actualizada.emit();
      })
      .catch((err) => {
        this.error.set(errorMessage(err));
        const details = (err as { error?: { details?: Record<string, unknown> } })?.error?.details;
        const problems = details?.['problems'];
        if (Array.isArray(problems)) this.problemas.set(problems.map(String));
      })
      .finally(() => this.guardando.set(false));
  }

  protected descartarError(): void {
    this.error.set('');
    this.problemas.set([]);
  }
}
