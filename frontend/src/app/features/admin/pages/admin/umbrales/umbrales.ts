import { Component, computed, effect, inject, signal } from '@angular/core';
import { BandScale } from '../../../../../shared/components/band-scale/band-scale';
import { errorMessage } from '../../../../../shared/interceptors/error.interceptor';
import {
  UMBRALES_DEFECTO,
  UmbralesCalibracion,
} from '../../../../../shared/utils/decision';
import { formatearFecha } from '../../../../../shared/utils/format';
import { UmbralesService } from '../../../services/umbrales.service';

/**
 * Calibration-thresholds administration page (T-084, RF-28).
 *
 * Shows the stored integer thresholds (defaults 4/7 when never set) with a
 * live band-scale preview, validates them (integers 1-10, `rechazo <
 * aceptacion`) before saving, stores the new audited pair and reloads the
 * values (including `updatedBy`/`updatedAt`). Only administrators can reach
 * this page (RNF-7); 422 `THRESHOLDS_INVALID` problems are surfaced (RNF-3).
 */
@Component({
  selector: 'app-umbrales-page',
  imports: [BandScale],
  templateUrl: './umbrales.html',
})
export class UmbralesPage {
  private readonly umbralesService = inject(UmbralesService);

  /** The stored values (defaults 4/7 when never set). */
  protected readonly umbrales = this.umbralesService.umbrales;

  /** The current draft of the rejection threshold. */
  protected readonly rechazo = signal(UMBRALES_DEFECTO.rejectionThreshold);
  /** The current draft of the acceptance threshold. */
  protected readonly aceptacion = signal(UMBRALES_DEFECTO.acceptanceThreshold);
  /** `true` while the save is in flight. */
  protected readonly guardando = signal(false);
  /** `true` after a successful save. */
  protected readonly guardado = signal(false);
  /** The last backend error message to surface (RNF-3). */
  protected readonly error = signal('');
  /** The 422 `THRESHOLDS_INVALID` problems, when the backend rejected the save. */
  protected readonly problemas = signal<string[]>([]);

  private inicializado = false;

  constructor() {
    // Prefills the drafts with the stored values once they load (the first
    // time) so the form shows the persisted thresholds, not the defaults.
    effect(() => {
      const u = this.umbrales.value();
      if (u == null || this.inicializado) return;
      this.inicializado = true;
      this.rechazo.set(u.rejectionThreshold);
      this.aceptacion.set(u.acceptanceThreshold);
    });
  }

  /** The draft as the `GET/PUT` payload (for the live preview). */
  protected readonly umbralesBorrador = computed<UmbralesCalibracion>(() => ({
    rejectionThreshold: this.rechazo(),
    acceptanceThreshold: this.aceptacion(),
  }));

  /** The client-side validation message (`''` when the drafts are valid). */
  protected readonly mensajeValidacion = computed(() => {
    const r = this.rechazo();
    const a = this.aceptacion();
    const esEntero = (n: number) => Number.isInteger(n);
    if (!esEntero(r) || r < 1 || r > 10) {
      return 'El umbral de rechazo debe ser un entero entre 1 y 10.';
    }
    if (!esEntero(a) || a < 1 || a > 10) {
      return 'El umbral de aceptación debe ser un entero entre 1 y 10.';
    }
    if (r >= a) {
      return 'El umbral de rechazo debe ser menor que el umbral de aceptación.';
    }
    return '';
  });

  /** `true` when the form may be saved (client validation passed). */
  protected readonly valido = computed(() => this.mensajeValidacion() === '');

  protected setUmbral(campo: 'rechazo' | 'aceptacion', raw: string): void {
    const n = raw === '' ? 0 : Number.parseInt(raw, 10);
    if (campo === 'rechazo') this.rechazo.set(n);
    else this.aceptacion.set(n);
    this.guardado.set(false);
  }

  /** Stores the validated thresholds (RF-28). */
  protected guardar(): void {
    if (!this.valido() || this.guardando()) return;
    this.guardando.set(true);
    this.error.set('');
    this.problemas.set([]);
    this.guardado.set(false);
    void this.umbralesService
      .guardar(this.umbralesBorrador())
      .then(() => {
        this.guardado.set(true);
        this.umbrales.reload();
      })
      .catch((err) => {
        this.error.set(errorMessage(err));
        const body = (
          err as { error?: { code?: string; details?: Record<string, unknown> } }
        )?.error;
        if (body?.code === 'THRESHOLDS_INVALID') {
          const problemas = body.details?.['problems'];
          if (Array.isArray(problemas)) {
            this.problemas.set(problemas.filter((p): p is string => typeof p === 'string'));
          }
        }
      })
      .finally(() => {
        this.guardando.set(false);
      });
  }

  protected descartarError(): void {
    this.error.set('');
    this.problemas.set([]);
  }

  protected readonly formatearFecha = formatearFecha;
}
