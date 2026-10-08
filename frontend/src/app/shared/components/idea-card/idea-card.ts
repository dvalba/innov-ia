import { Component, input } from '@angular/core';
import { BadgeState } from '../badge-state/badge-state';
import { IdeaFieldsPublica, IdeaState } from '../../types/models';
import { CAMPOS_DEF, formatearDetalle } from '../../utils/idea-fields';

/**
 * Shared idea card (T-056, RF-19/RF-14, Constitution §3.2).
 *
 * One card, two variants, promoted to `shared` because it is reused by three
 * features (my-ideas, validation, catalog) with no cross-feature imports:
 *   - `compact`: a single list row — title + one meta line plus, when a state
 *     is given, the state badge and an affordance arrow. It is deliberately a
 *     plain element: the caller decides how it is opened (wraps it in a
 *     `routerLink`, adds a click handler, …), so the card stays feature-free.
 *   - `full`: a header (title, the caller's pre-formatted meta lines and the
 *     proponent's name/area — never the contact, RF-14) plus the read-only
 *     7-field grid (`IdeaFieldsPublica`, the proponent field excluded from the
 *     grid) and an actions slot (`<ng-content select="[idea-card-actions]">`)
 *     the caller fills with its own banner/buttons.
 *
 * The card is intentionally dumb: the caller pre-formats the meta lines and
 * passes the public field shape, so the 7-field rendering stays identical
 * everywhere (driven by the shared `idea-fields` metadata).
 */
@Component({
  selector: 'app-idea-card',
  imports: [BadgeState],
  templateUrl: './idea-card.html',
})
export class IdeaCard {
  /** Which layout to render. */
  readonly variant = input<'compact' | 'full'>('full');
  /** The idea title (renders "Sin título" when empty). */
  readonly titulo = input.required<string>();
  /** The single meta line for the `compact` variant (Spanish, caller-built). */
  readonly metaCompacta = input('');
  /** Pre-formatted header meta lines for the `full` variant. */
  readonly meta = input<string[]>([]);
  /** Proponent name/area for the `full` header (public shape, no contact). */
  readonly proponente = input<{ name: string; area: string } | null>(null);
  /** The 7-field public shape for the `full` read-only grid. */
  readonly campos = input<IdeaFieldsPublica | null>(null);
  /** The idea state, rendered as a badge in the `compact` variant. */
  readonly estado = input<IdeaState | null>(null);

  protected readonly CAMPOS_DEF = CAMPOS_DEF;
  protected readonly formatearDetalle = formatearDetalle;
}
