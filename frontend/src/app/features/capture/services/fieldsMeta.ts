/**
 * Capture field metadata (T-040, RF-3/RF-5, RNF-4).
 *
 * Client mirror of the backend's fixed capture contract (`capture_rules`,
 * decision D7): the exact order of the 7 questions, the Spanish question per
 * field and the fixed quick-reply catalog per field. The backend remains the
 * source of truth; this mirror feeds the UI (progress, chip labels,
 * placeholders) without drifting from D7.
 */

/** RF-3: the fixed order of the 7 capture questions (mirror of the backend). */
export const FIELD_ORDER = [
  'description',
  'title',
  'problem',
  'expectedBenefit',
  'strategicAlignment',
  'estimatedResources',
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
  estimatedResources: 'Recursos estimados',
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
  estimatedResources:
    '¿Qué recursos estimas necesitas? Indícame tiempo, personal y presupuesto.',
  proponent:
    'Por último, estos son tus datos de proponente registrados en tu cuenta. ' +
    'Confírmame si están bien o escríbeme la corrección.',
};

/**
 * D7/RF-5: the FIXED quick-reply catalog per field. A chip is the field's
 * complete answer. The free description and the suggested title (RF-4) have no
 * catalog.
 */
export const CHIPS_BY_FIELD: Record<FieldName, readonly string[]> = {
  description: [],
  title: [],
  problem: [
    'Retrasos en la operación actual',
    'Tarea manual repetitiva',
    'Costos elevados del proceso actual',
    'Falta de visibilidad del área',
  ],
  expectedBenefit: [
    'Ahorro de tiempo operativo',
    'Reducción de costos',
    'Mejor atención al cliente',
    'Generación de ingresos nuevos',
  ],
  strategicAlignment: [
    'Agilizar procesos internos',
    'Reducir la carga administrativa manual',
    'Mejorar la experiencia del cliente',
    'Alinear con los objetivos estratégicos del año',
  ],
  estimatedResources: [
    'Bajo: menos de un mes',
    'Medio: de 1 a 3 meses',
    'Alto: más de 3 meses',
  ],
  proponent: ['Confirmar mi información', 'Corregir mi información'],
};

/** The two structured fields (plan §2.2) carried as JSON strings. */
export const STRUCTURED_FIELDS: readonly FieldName[] = ['proponent', 'estimatedResources'];

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

/** The editable 7-field form shared by the summary (RF-6) and the manual form (RF-7). */
export interface FormResumen {
  title: string;
  description: string;
  problem: string;
  expectedBenefit: string;
  strategicAlignment: string;
  proponent: { name: string; area: string; contact: string };
  estimatedResources: { time: string; people: string; budget: string };
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
 * Builds the editable 7-field form from a raw field map (the RESUMEN summary or
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
  const est = objeto(base['estimatedResources']) ?? {};
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
    estimatedResources: {
      time: est['time'] ?? '',
      people: est['people'] ?? '',
      budget: est['budget'] ?? '',
    },
  };
}

/** True when the form is complete: all 7 parts non-empty + a valid contact (RNF-5, case 12). */
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
    f.estimatedResources.time,
    f.estimatedResources.people,
    f.estimatedResources.budget,
  ].every((t) => t.trim() !== '');
  return textosLlenos && contactoValido(f.proponent.contact);
}
