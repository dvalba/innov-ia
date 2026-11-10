import { EvaluacionEstado } from '../types/models';

/**
 * Shared evaluation display metadata (RF-26, RNF-2/RNF-5, T-077).
 *
 * Neutral, feature-agnostic rendering of the fixed 5-criterion evaluation
 * contract: the canonical order, the Spanish label per criterion and the
 * Spanish label of the lifecycle state. Mirrors the shared backend contract
 * (`shared/contracts/evaluation.py`).
 */

/** The fixed order of the 5 evaluation criteria (RF-26, decision D15). */
export const EVALUATION_CRITERIA_KEYS = [
  'claridadDelProblema',
  'factibilidad',
  'impactoEsperado',
  'alineacionEstrategica',
  'gradoDeInnovacion',
] as const;

/** A criterion key of the 5-criterion contract. */
export type CriterioClave = (typeof EVALUATION_CRITERIA_KEYS)[number];

/** Spanish label per criterion (UI copy, RNF-4). */
export const CRITERIO_LABEL: Record<CriterioClave, string> = {
  claridadDelProblema: 'Claridad del problema',
  factibilidad: 'Factibilidad',
  impactoEsperado: 'Impacto esperado',
  alineacionEstrategica: 'Alineación estratégica',
  gradoDeInnovacion: 'Grado de innovación',
};

/** A criterion row for templates: the key plus its Spanish label. */
export interface CriterioDef {
  clave: CriterioClave;
  etiqueta: string;
}

/** The ordered list of criterion rows for templates (`@for` over objects). */
export const CRITERIOS_EVALUACION: CriterioDef[] = EVALUATION_CRITERIA_KEYS.map((k) => ({
  clave: k,
  etiqueta: CRITERIO_LABEL[k],
}));

/** Spanish label for the evaluation lifecycle state (RNF-4). */
export function evaluacionEstadoLabel(status: EvaluacionEstado | string): string {
  switch (status) {
    case 'PENDING':
      return 'Pendiente (IA no disponible)';
    case 'GENERADA':
      return 'Generada por la IA';
    case 'ACEPTADA':
      return 'Aceptada';
    case 'SUSTITUIDA':
      return 'Sustituida';
    default:
      return status;
  }
}
