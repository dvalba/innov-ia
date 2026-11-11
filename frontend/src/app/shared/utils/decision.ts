/**
 * Calibration decision helpers (T-084, RF-27/RF-28, RNF-2).
 *
 * Pure frontend mirror of the backend rules (`decision_rules.py`,
 * `threshold_rules.py`): the average of the 5 criteria rounded to 2 decimals
 * and the band derived from the calibration thresholds. The frontend uses the
 * documented defaults as a preview only — the backend `409 DECISION_MISMATCH`
 * is the authority when a decision is submitted (D13 of v2.2).
 */

import { DecisionOutcome } from '../types/models';

/** Calibration thresholds (the shape used by `GET /admin/calibration-thresholds`). */
export interface UmbralesCalibracion {
  rejectionThreshold: number;
  acceptanceThreshold: number;
}

/** The documented default calibration thresholds (RF-28, case 31). */
export const UMBRALES_DEFECTO: UmbralesCalibracion = {
  rejectionThreshold: 4,
  acceptanceThreshold: 7,
};

/**
 * The average of the given scores, rounded to 2 decimals (same rule as the
 * backend). Returns `null` for an empty list.
 */
export function promedioDe(scores: readonly number[]): number | null {
  if (scores.length === 0) return null;
  const total = scores.reduce((acc, s) => acc + s, 0);
  return Math.round((total / scores.length) * 100) / 100;
}

/**
 * The band for an average against the given thresholds (defaults when
 * omitted): `avg < rejection` -> RECHAZADA, `rejection <= avg < acceptance`
 * -> ARCHIVADA, `avg >= acceptance` -> ACEPTADA.
 */
export function bandaDe(promedio: number, umbrales: UmbralesCalibracion = UMBRALES_DEFECTO): DecisionOutcome {
  if (promedio < umbrales.rejectionThreshold) return 'RECHAZADA';
  if (promedio < umbrales.acceptanceThreshold) return 'ARCHIVADA';
  return 'ACEPTADA';
}

/** Spanish label of a final outcome (RNF-4). */
export function resultadoLabel(outcome: DecisionOutcome): string {
  switch (outcome) {
    case 'ACEPTADA':
      return 'Aceptada';
    case 'ARCHIVADA':
      return 'Archivada';
    case 'RECHAZADA':
      return 'Rechazada';
  }
}

/** The three band labels in display order (lowest first). */
export const BANDA_LABEL: Record<DecisionOutcome, string> = {
  RECHAZADA: 'Rechazadas',
  ARCHIVADA: 'Archivadas',
  ACEPTADA: 'Aprobadas',
};
