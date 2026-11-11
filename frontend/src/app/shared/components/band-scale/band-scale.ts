import { Component, computed, input } from '@angular/core';
import {
  BANDA_LABEL,
  UMBRALES_DEFECTO,
  UmbralesCalibracion,
} from '../../utils/decision';

/**
 * Band scale (T-084, RF-27/RF-28; reusable by T-085).
 *
 * Presentational rendering of the average of the 5 criteria against the
 * calibration thresholds: a horizontal 0–10 scale (rendered 0–100%) segmented
 * in the three bands — `Rechazadas` (0 → rejection), `Archivadas`
 * (rejection → acceptance) and `Aprobadas` (acceptance → 10) — with a marker
 * at the current average and the average shown as a percentage. The bands are
 * closed upward (case 26). Pure display: it never computes anything the caller
 * has not given (the average, the thresholds); the decision outcome is derived
 * by the caller with `bandaDe` (same pure rule as the backend).
 */
@Component({
  selector: 'app-band-scale',
  templateUrl: './band-scale.html',
})
export class BandScale {
  /** The average of the 5 criteria (1–10); `null` = no marker. */
  readonly promedio = input<number | null>(null);
  /** The calibration thresholds (defaults 4/7 when omitted). */
  readonly umbrales = input<UmbralesCalibracion>(UMBRALES_DEFECTO);
  /** The scale title (Spanish, RNF-4). */
  readonly titulo = input('PROMEDIO DE LOS 5 CRITERIOS · 3 SECCIONES');

  /** Position of the marker in % (average 1–10 over the 0–100% track). */
  protected readonly marcadorPos = computed(() => {
    const p = this.promedio();
    return p == null ? null : Math.min(Math.max(p, 0), 10) * 10;
  });

  /** The average as a percentage (e.g. "68,3%"). */
  protected readonly promedioPct = computed(() => {
    const p = this.promedio();
    return p == null ? null : (p * 10).toFixed(1).replace('.', ',') + '%';
  });

  /** The marker color, by the band the average falls into (case 26). */
  protected readonly marcadorClase = computed(() => {
    const p = this.promedio();
    if (p == null) return '';
    const u = this.umbrales();
    if (p < u.rejectionThreshold) return 'bg-red-600 dark:bg-red-400';
    if (p < u.acceptanceThreshold) return 'bg-slate-600 dark:bg-slate-300';
    return 'bg-emerald-600 dark:bg-emerald-400';
  });

  /** The three bands in display order with their width in %. */
  protected readonly secciones = computed(() => {
    const u = this.umbrales();
    return [
      {
        etiqueta: BANDA_LABEL.RECHAZADA,
        ancho: u.rejectionThreshold * 10,
        clase: 'bg-red-200/70 dark:bg-red-500/25',
        dot: 'bg-red-500',
      },
      {
        etiqueta: BANDA_LABEL.ARCHIVADA,
        ancho: (u.acceptanceThreshold - u.rejectionThreshold) * 10,
        clase: 'bg-slate-200/70 dark:bg-slate-500/25',
        dot: 'bg-slate-400',
      },
      {
        etiqueta: BANDA_LABEL.ACEPTADA,
        ancho: (10 - u.acceptanceThreshold) * 10,
        clase: 'bg-emerald-200/70 dark:bg-emerald-500/25',
        dot: 'bg-emerald-500',
      },
    ];
  });
}
