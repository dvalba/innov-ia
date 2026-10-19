/**
 * Capture field metadata (T-040, RF-3/RF-5, RNF-4).
 *
 * Client mirror of the backend's fixed capture contract (`capture_rules`,
 * decision D7): the exact order of the 6 questions and the Spanish question
 * per field. The quick replies are NOT a client catalog: the backend offers
 * them per turn (IA-generated, D7 replacement) and the UI renders the turn's
 * `quickOptions` as they arrive.
 */

/** RF-3: the fixed order of the 6 capture questions (mirror of the backend). */
export const FIELD_ORDER = [
  'description',
  'title',
  'problem',
  'expectedBenefit',
  'strategicAlignment',
  'proponent',
] as const;

/** A capture field name. */
export type FieldName = (typeof FIELD_ORDER)[number];

/** Short Spanish label per field (UI copy, RNF-4). */
export const FIELD_LABEL: Record<FieldName, string> = {
  description: 'Descripción',
  title: 'Título',
  problem: 'Problema u oportunidad',
  expectedBenefit: 'Beneficio esperado',
  strategicAlignment: 'Alineación estratégica',
  proponent: 'Proponente',
};

/** RF-3: the question asked per field (Spanish mirror of the backend). */
export const QUESTION_BY_FIELD: Record<FieldName, string> = {
  description:
    'Para empezar: cuéntame, ¿de qué trata tu idea? Escríbela en tus propias ' +
    'palabras y tan libremente como quieras; si en el texto aparecen datos de ' +
    'otros campos, los capturo directamente.',
  title:
    'Ya tengo una primera visión de tu idea. Aquí va mi sugerencia de título; ' +
    'puedes aceptarla, pedir otra, o escribir la que prefieras.',
  problem: '¿Cuál es el problema u oportunidad que tu idea aborda?',
  expectedBenefit: '¿Qué beneficio esperado genera para la organización?',
  strategicAlignment: '¿Cómo se alinea tu idea con la estrategia de la organización?',
  proponent:
    'Por último, estos son tus datos de proponente registrados en tu cuenta. ' +
    'Confírmame si están bien o escríbeme la corrección.',
};

/** The single structured field (plan §2.2) carried as a JSON string. */
export const STRUCTURED_FIELDS: readonly FieldName[] = ['proponent'];

/**
 * Parses a structured field's JSON string back into its object (mirror of the
 * backend's `field_object`); returns the raw text when it is not a valid JSON
 * object.
 */
export function parseStructuredField(raw: string | undefined | null): unknown {
  if (raw === undefined || raw === null || raw.trim() === '') return undefined;
  if (typeof raw === 'object') return raw; // already an object (summary)
  try {
    const parsed: unknown = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : raw;
  } catch {
    return raw;
  }
}

/** The editable 6-field form shared by the summary (RF-6) and the manual form (RF-7). */
export interface FormResumen {
  title: string;
  description: string;
  problem: string;
  expectedBenefit: string;
  strategicAlignment: string;
  proponent: { name: string; area: string; contact: string };
}

// Case 12: a valid contact is an e-mail or a 7–15 digit phone (mirror of the
// `ideas` domain validator); the UI only uses it to enable the send, the domain
// remains the source of truth.
const _EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const _PHONE_CHARS_RE = /[\s\-().]+/g;

/** True when `contact` is a well-formed e-mail or phone (case 12). */
export function contactoValido(contacto: string): boolean {
  const v = contacto.trim();
  if (!v) return false;
  if (_EMAIL_RE.test(v)) return true;
  const digits = v.replace(_PHONE_CHARS_RE, '').replace(/^\+/, '');
  return /^\d+$/.test(digits) && digits.length >= 7 && digits.length <= 15;
}

function _texto(valor: unknown): string {
  if (valor === undefined || valor === null) return '';
  if (typeof valor === 'string') return valor;
  return String(valor);
}

/**
 * Builds the editable 6-field form from a raw field map (the RESUMEN summary or
 * the contingency `capturedFields`). `cuenta` (the account proponent) fills any
 * missing proponent part, as in the manual contingency (RNF-10: nothing is lost
 * and the proponent is prefilled from the account).
 */
export function construirResumen(
  base: Record<string, unknown>,
  cuenta?: { name: string; area: string; contact: string },
): FormResumen {
  const objeto = (valor: unknown): Record<string, string | undefined> | undefined => {
    if (typeof valor === 'object' && valor !== null) return valor as Record<string, string>;
    const parseado = parseStructuredField(valor as string | undefined);
    return typeof parseado === 'object' && parseado !== null
      ? (parseado as Record<string, string>)
      : undefined;
  };
  const pro = objeto(base['proponent']) ?? {};
  const parte = (val: string | undefined, fallback: string) =>
    val && val.trim() !== '' ? val : fallback;
  return {
    title: _texto(base['title']),
    description: _texto(base['description']),
    problem: _texto(base['problem']),
    expectedBenefit: _texto(base['expectedBenefit']),
    strategicAlignment: _texto(base['strategicAlignment']),
    proponent: {
      name: parte(pro['name'], cuenta?.name ?? ''),
      area: parte(pro['area'], cuenta?.area ?? ''),
      contact: parte(pro['contact'], cuenta?.contact ?? ''),
    },
  };
}

/** True when the form is complete: all 6 parts non-empty + a valid contact (RNF-5, case 12). */
export function resumenCompleto(f: FormResumen): boolean {
  const textosLlenos = [
    f.title,
    f.description,
    f.problem,
    f.expectedBenefit,
    f.strategicAlignment,
    f.proponent.name,
    f.proponent.area,
    f.proponent.contact,
  ].every((t) => t.trim() !== '');
  return textosLlenos && contactoValido(f.proponent.contact);
}

/**
 * Spanish labels of the required parts still missing on the form (empty text,
 * or a contact that is not a valid e-mail/phone) so the UI can tell the
 * proponent exactly what to complete (UX: required `*` markers never explain
 * which field is the one blocking the send).
 */
export function faltantes(f: FormResumen): string[] {
  const faltan: string[] = [];
  const vacio = (valor: string) => valor.trim() === '';
  if (vacio(f.title)) faltan.push('título');
  if (vacio(f.description)) faltan.push('descripción');
  if (vacio(f.problem)) faltan.push('problema u oportunidad');
  if (vacio(f.expectedBenefit)) faltan.push('beneficio esperado');
  if (vacio(f.strategicAlignment)) faltan.push('alineación estratégica');
  if (vacio(f.proponent.name)) faltan.push('proponente: nombre');
  if (vacio(f.proponent.area)) faltan.push('proponente: área');
  if (vacio(f.proponent.contact)) faltan.push('proponente: contacto');
  else if (!contactoValido(f.proponent.contact)) {
    faltan.push('proponente: contacto inválido (usa un correo o un teléfono)');
  }
  return faltan;
}
