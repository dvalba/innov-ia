import { Idea, IdeaFields, VersionRequestedBy } from '../../../shared/types/models';
import {
  CAMPOS,
  CAMPOS_DEF,
  CampoClave,
  difiere,
  formatearDetalle,
  origenLabel,
} from '../../../shared/utils/idea-fields';

export { CAMPOS, CAMPOS_DEF, difiere, formatearDetalle, origenLabel };
export type { CampoClave };

/**
 * "Mis ideas" field metadata (T-047/T-049, RF-9/RF-13).
 *
 * The fixed 6-field contract shared by the manual edit form (RF-9) and the
 * refined-vs-original comparison (RF-13). The read-only display metadata
 * (order, Spanish labels, read-only rendering, field diff) is re-exported from
 * the neutral shared module so every feature renders the fields identically;
 * only the editable-form helpers (completeness, payload mapping) live here,
 * since they operate on the full owner-side `Idea`/`IdeaFields` shapes. The
 * backend remains the source of truth (RNF-2); this module only drives the UI.
 */

/** Spanish label for the origin of an `IdeaVersion` (RF-8/RF-13). */
export function versionOrigenLabel(origin: VersionRequestedBy | string): string {
  switch (origin) {
    case 'refinement':
      return 'Refinamiento';
    case 'improvement':
      return 'Mejora solicitada';
    case 'adjustment':
      return 'Ajuste en el chat';
    default:
      return origin;
  }
}

/** `true` when the 6-field form is complete (all parts non-empty, case 12 UI guard). */
export function formCompleto(f: IdeaFields): boolean {
  const textos = [f.title, f.description, f.problem, f.expectedBenefit, f.strategicAlignment].every(
    (t) => t.trim() !== '',
  );
  const prop = f.proponent;
  const proOk = prop && prop.name.trim() !== '' && prop.area.trim() !== '' && prop.contact.trim() !== '';
  return textos && !!proOk;
}

/** Builds the editable 6-field form from an idea payload (manual edit, RF-9). */
export function formDesdeIdea(idea: Idea): IdeaFields {
  return {
    title: idea.title,
    description: idea.description,
    problem: idea.problem,
    expectedBenefit: idea.expectedBenefit,
    strategicAlignment: idea.strategicAlignment,
    proponent: { ...idea.proponent },
  };
}

/** Compiles the editable form back into the 6-field payload for the PUT. */
export function camposParaPut(f: IdeaFields): IdeaFields {
  return {
    title: f.title,
    description: f.description,
    problem: f.problem,
    expectedBenefit: f.expectedBenefit,
    strategicAlignment: f.strategicAlignment,
    proponent: { ...f.proponent },
  };
}
