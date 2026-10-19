import { IdeaOrigin } from '../types/models';

/**
 * Shared 6-field idea display metadata (plan §2.2, RNF-2/RNF-5).
 *
 * Neutral, feature-agnostic rendering of the fixed 6-field contract: the
 * display order, the Spanish label per field and the read-only textual
 * rendering used by every surface that shows the fields without editing
 * ("Mis ideas" detail, the specialist validation queue and the public
 * catalog). It intentionally accepts a proponent without `contact` (the
 * queue/catalog public shapes) and renders only what is present.
 */

/** The fixed display order of the 6 fields. */
export const CAMPOS = [
  'title',
  'description',
  'problem',
  'expectedBenefit',
  'strategicAlignment',
  'proponent',
] as const;

/** A field key of the 6-field contract. */
export type CampoClave = (typeof CAMPOS)[number];

/** Spanish label per field (UI copy, RNF-4). */
export const CAMPO_LABEL: Record<CampoClave, string> = {
  title: 'Título',
  description: 'Descripción',
  problem: 'Problema u oportunidad',
  expectedBenefit: 'Beneficio esperado',
  strategicAlignment: 'Alineación estratégica',
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

/** Textual rendering of a proponent value (only the parts present, RNF-7). */
function proponentTexto(v: unknown): string {
  if (!v || typeof v !== 'object') return '—';
  const o = v as Record<string, unknown>;
  const partes = [o['name'], o['area'], o['contact']]
    .map((p) => (typeof p === 'string' ? p : ''))
    .filter(Boolean);
  return partes.length ? partes.join(' — ') : '—';
}

/**
 * Renders a field value into display text for the read-only rows. Tolerates
 * the public proponent shape (name/area, no contact) by rendering only the
 * present parts.
 */
export function formatearDetalle(clave: CampoClave, valor: unknown): string {
  if (clave === 'proponent') return proponentTexto(valor);
  const t = typeof valor === 'string' ? valor : String(valor ?? '');
  return t.trim() === '' ? '—' : t;
}

/** Compares two field values field-by-field (RF-13, refined-vs-original). */
export function difiere(clave: CampoClave, original: unknown, refino: unknown): boolean {
  if (clave === 'proponent') {
    const a = (original ?? {}) as Record<string, unknown>;
    const b = (refino ?? {}) as Record<string, unknown>;
    const keys = Array.from(new Set([...Object.keys(a), ...Object.keys(b)]));
    return keys.some((k) => String(a[k] ?? '') !== String(b[k] ?? ''));
  }
  const av = typeof original === 'string' ? original : String(original ?? '');
  const bv = typeof refino === 'string' ? refino : String(refino ?? '');
  return av.trim() !== bv.trim();
}
