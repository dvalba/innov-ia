import { Idea, IdeaFields, IdeaOrigin, VersionRequestedBy } from '../../../shared/types/models';

/**
 * "Mis ideas" field metadata (T-047/T-049, RF-9/RF-13).
 *
 * The fixed 7-field contract shared by the manual edit form (RF-9) and the
 * refined-vs-original comparison (RF-13): the display order, the Spanish label
 * per field, a display rendering for the read-only rows, the completeness check
 * (case 12) and the helpers that move between the backend `Idea` payload and
 * the editable form. The backend remains the source of truth (RNF-2); this
 * module only drives the UI.
 */

/** The fixed display order of the 7 fields. */
export const CAMPOS = [
  'title',
  'description',
  'problem',
  'expectedBenefit',
  'strategicAlignment',
  'estimatedResources',
  'proponent',
] as const;

/** A field key of the 7-field contract. */
export type CampoClave = (typeof CAMPOS)[number];

/** Spanish label per field (UI copy, RNF-4). */
export const CAMPO_LABEL: Record<CampoClave, string> = {
  title: 'Título',
  description: 'Descripción',
  problem: 'Problema u oportunidad',
  expectedBenefit: 'Beneficio esperado',
  strategicAlignment: 'Alineación estratégica',
  estimatedResources: 'Recursos estimados',
  proponent: 'Proponente',
};

/** A field row for templates: the key plus its Spanish label. */
export interface CampoDef {
  clave: CampoClave;
  etiqueta: string;
}

/** The ordered list of field rows for templates (`@for` over objects). */
export const CAMPOS_DEF: CampoDef[] = CAMPOS.map((c) => ({ clave: c, etiqueta: CAMPO_LABEL[c] }));

/** Spanish label for the idea origin (RNF-4). */
export function origenLabel(origin: IdeaOrigin | string): string {
  if (origin === 'asistida') return 'Asistida';
  if (origin === 'manual') return 'Manual';
  return origin;
}

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

/** `true` when the 7-field form is complete (all parts non-empty, case 12 UI guard). */
export function formCompleto(f: IdeaFields): boolean {
  const textos = [f.title, f.description, f.problem, f.expectedBenefit, f.strategicAlignment].every(
    (t) => t.trim() !== '',
  );
  const prop = f.proponent;
  const proOk = prop && prop.name.trim() !== '' && prop.area.trim() !== '' && prop.contact.trim() !== '';
  const est = f.estimatedResources;
  const estOk =
    est && est.time.trim() !== '' && est.people.trim() !== '' && est.budget.trim() !== '';
  return textos && !!proOk && !!estOk;
}

/** Textual rendering of a proponent value. */
function proponentTexto(v: unknown): string {
  if (!v || typeof v !== 'object') return '—';
  const o = v as Record<string, unknown>;
  const partes = [o['name'], o['area'], o['contact']].map((p) => (typeof p === 'string' ? p : '')).filter(Boolean);
  return partes.length ? partes.join(' — ') : '—';
}

/** Textual rendering of an estimated-resources value. */
function recursosTexto(v: unknown): string {
  if (!v || typeof v !== 'object') return '—';
  const o = v as Record<string, unknown>;
  const partes = [o['time'], o['people'], o['budget']]
    .map((x) => (typeof x === 'string' && x.trim() !== '' ? x : ''))
    .filter(Boolean);
  return partes.length ? partes.join(' · ') : '—';
}

/** Renders a field value into display text for the read-only detail rows. */
export function formatearDetalle(clave: CampoClave, valor: unknown): string {
  if (clave === 'proponent') return proponentTexto(valor);
  if (clave === 'estimatedResources') return recursosTexto(valor);
  const t = typeof valor === 'string' ? valor : String(valor ?? '');
  return t.trim() === '' ? '—' : t;
}

/** Compares two field values field-by-field (RF-13, refined-vs-original). */
export function difiere(clave: CampoClave, original: unknown, refino: unknown): boolean {
  if (clave === 'proponent' || clave === 'estimatedResources') {
    const a = (original ?? {}) as Record<string, unknown>;
    const b = (refino ?? {}) as Record<string, unknown>;
    const keys = Array.from(new Set([...Object.keys(a), ...Object.keys(b)]));
    return keys.some((k) => String(a[k] ?? '') !== String(b[k] ?? ''));
  }
  const av = typeof original === 'string' ? original : String(original ?? '');
  const bv = typeof refino === 'string' ? refino : String(refino ?? '');
  return av.trim() !== bv.trim();
}

/** Builds the editable 7-field form from an idea payload (manual edit, RF-9). */
export function formDesdeIdea(idea: Idea): IdeaFields {
  return {
    title: idea.title,
    description: idea.description,
    problem: idea.problem,
    expectedBenefit: idea.expectedBenefit,
    strategicAlignment: idea.strategicAlignment,
    proponent: { ...idea.proponent },
    estimatedResources: { ...idea.estimatedResources },
  };
}

/** Compiles the editable form back into the 7-field payload for the PUT. */
export function camposParaPut(f: IdeaFields): IdeaFields {
  return {
    title: f.title,
    description: f.description,
    problem: f.problem,
    expectedBenefit: f.expectedBenefit,
    strategicAlignment: f.strategicAlignment,
    proponent: { ...f.proponent },
    estimatedResources: { ...f.estimatedResources },
  };
}
