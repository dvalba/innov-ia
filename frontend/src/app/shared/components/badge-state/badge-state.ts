import { Component, input } from '@angular/core';
import { IdeaState } from '../../types/models';
import { estadoLabel } from '../../utils/state';

/** Tailwind classes per state (shared palette: slate/indigo, RNF-4/consistency). */
const BADGE_CLASSES: Record<IdeaState, string> = {
  EN_DESARROLLO:
    'bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-500/15 dark:text-amber-300 dark:ring-amber-500/30',
  SOLICITANDO_PUBLICACION:
    'bg-indigo-50 text-indigo-700 ring-indigo-200 dark:bg-indigo-500/15 dark:text-indigo-300 dark:ring-indigo-500/30',
  VALIDADA_PUBLICA:
    'bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-300 dark:ring-emerald-500/30',
  ACEPTADA:
    'bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-300 dark:ring-emerald-500/30',
  ARCHIVADA:
    'bg-slate-100 text-slate-600 ring-slate-200 dark:bg-slate-500/15 dark:text-slate-300 dark:ring-slate-500/30',
  RECHAZADA:
    'bg-red-50 text-red-700 ring-red-200 dark:bg-red-500/15 dark:text-red-300 dark:ring-red-500/30',
};

/**
 * Idea state badge (T-009, RNF-2, plan §1.1).
 *
 * Renders an idea state with a Spanish label and a color per state. It is a
 * focusable, labelled element so it remains reachable with a keyboard and
 * with a screen reader (RNF-6).
 */
@Component({
  selector: 'app-badge-state',
  template: `
    <span
      tabindex="0"
      [attr.aria-label]="'Estado: ' + estadoLabel(estado())"
      class="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 focus:outline-none focus:ring-2"
      [class]="BADGE_CLASSES[estado()]"
    >
      <span
        class="h-1.5 w-1.5 rounded-full"
        [class]="DOT_CLASSES[estado()]"
        aria-hidden="true"
      ></span>
      {{ estadoLabel(estado()) }}
    </span>
  `,
})
export class BadgeState {
  /** The idea state to display (plan §2.2). */
  readonly estado = input.required<IdeaState>();

  protected readonly estadoLabel = estadoLabel;
  protected readonly BADGE_CLASSES = BADGE_CLASSES;
  protected readonly DOT_CLASSES: Record<IdeaState, string> = {
    EN_DESARROLLO: 'bg-amber-500',
    SOLICITANDO_PUBLICACION: 'bg-indigo-500',
    VALIDADA_PUBLICA: 'bg-emerald-500',
    ACEPTADA: 'bg-emerald-500',
    ARCHIVADA: 'bg-slate-400',
    RECHAZADA: 'bg-red-500',
  };
}
