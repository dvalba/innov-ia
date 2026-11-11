import { httpResource } from '@angular/common/http';
import { Component, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';
import { BadgeState } from '../../../../shared/components/badge-state/badge-state';
import { IdeaCard } from '../../../../shared/components/idea-card/idea-card';
import { CalibrationEvaluation } from '../calibration-evaluation/calibration-evaluation';
import { CalibrationDecision } from '../calibration-decision/calibration-decision';
import { origenLabel } from '../../../../shared/utils/idea-fields';
import { formatearFecha } from '../../../../shared/utils/format';
import {
  Debate,
  DecisionOutcome,
  IdeaCola,
  IdeaDetallePublica,
} from '../../../../shared/types/models';

/**
 * Calibration-queue panel (T-084, RF-14/RF-23/RF-26/RF-27).
 *
 * Renders one entry of the calibration stage: the full ficha (the 6 fields,
 * the state badge, the origin + publication date), the compact debate (the
 * closure summary + a read-only link to the full debate in the catalog) and
 * the two specialist work surfaces — the AI evaluation (accept/replace) and
 * the final decision. It only consumes the `validation` (G10) and the public
 * `catalog` contracts through its own `httpResource` reads (RNF-2); every
 * mutation is owned by the children, whose `terminada` events reload the
 * detail so the ficha always reflects the last action.
 */
@Component({
  selector: 'app-calibration-panel',
  imports: [RouterLink, BadgeState, IdeaCard, CalibrationEvaluation, CalibrationDecision],
  templateUrl: './calibration-panel.html',
})
export class CalibrationPanel {
  /** The queue entry being calibrated. */
  readonly entrada = input.required<IdeaCola>();
  /** `true` while the parent processes a decision (locks every panel). */
  readonly ocupado = input(false);
  /** A child mutation started, so the parent can lock the other panels. */
  readonly comenzada = output<void>();
  /** A child mutation finished (success or failure) so the parent can unlock. */
  readonly terminada = output<void>();
  /** The final decision was recorded so the parent can confirm and reload. */
  readonly decidida = output<DecisionOutcome>();

  /** GET /catalog/{id} — the full public detail (fields, state, evaluation). */
  private readonly detalle = httpResource<IdeaDetallePublica>(() =>
    `/catalog/${this.entrada().id}`,
  );

  /** GET /catalog/{id}/debate — the closed debate (summary + closure date). */
  private readonly debate = httpResource<Debate>(() =>
    `/catalog/${this.entrada().id}/debate`,
  );

  /** The loaded detail (null while loading or on error). */
  protected readonly detalleValue = this.detalle.value;

  /** `true` when the detail failed to load (RNF-3). */
  protected readonly detalleError = this.detalle.error;

  /** The loaded debate (null while loading or on error). */
  protected readonly debateValue = this.debate.value;

  protected readonly formatearFecha = formatearFecha;
  protected readonly origenLabel = origenLabel;

  /** The header meta line (publication date + origin, pre-formatted). */
  protected metaLinea(): string {
    const d = this.detalleValue();
    return `Publicada el ${formatearFecha(d?.publishedAt ?? null)} · Origen ${origenLabel(
      this.entrada().origin,
    )}`;
  }

  /** Forwards the child's mutation start to the parent. */
  protected onComenzada(): void {
    this.comenzada.emit();
  }

  /** Reloads the detail after any evaluation change, then unlocks the parent. */
  protected onTerminadaEvaluacion(): void {
    this.detalle.reload();
    this.terminada.emit();
  }

  /** Reloads the detail after a final decision, then unlocks the parent. */
  protected onTerminadaDecision(): void {
    this.detalle.reload();
    this.terminada.emit();
  }

  /** Forwards the recorded outcome so the parent can confirm and reload. */
  protected onDecidida(outcome: DecisionOutcome): void {
    this.decidida.emit(outcome);
  }
}
