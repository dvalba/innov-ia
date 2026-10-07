import { Component, input, output } from '@angular/core';
import {
  CAMPOS_DEF,
  difiere,
  formatearDetalle,
} from '../../services/my-idea-fields';
import { Idea, IdeaVersion } from '../../../../shared/types/models';
import { formatearDia } from '../../../../shared/utils/format';

/**
 * Refined-vs-original comparison (T-049, RF-13).
 *
 * Shows a pending refinement version field by field against the current idea,
 * highlighting only what changed, with two actions: "Aceptar la versión"
 * (decide; the idea stays EN_DESARROLLO) and "Ajustar detalles en el chat"
 * (the precontextualized conversation; when the assistant is unavailable the
 * manual-editing fallback applies — RF-9). UI copy in Spanish (RNF-4).
 */
@Component({
  selector: 'app-refine-view',
  templateUrl: './refine-view.html',
})
export class RefineView {
  /** The pending refined version to compare. */
  readonly version = input.required<IdeaVersion>();
  /** The current (original) idea. */
  readonly idea = input.required<Idea>();
  /** Accept this refined version (delegated to the parent decide). */
  readonly aceptar = output<IdeaVersion>();
  /** Request to tune the refinement in the precontextualized conversation. */
  readonly ajustar = output<IdeaVersion>();
  /** `true` while the parent is processing the accept decision. */
  readonly ocupado = input(false);

  protected readonly campos = CAMPOS_DEF;
  protected readonly difiere = difiere;
  protected readonly formatearDetalle = formatearDetalle;
  protected readonly formatearDia = formatearDia;
}
