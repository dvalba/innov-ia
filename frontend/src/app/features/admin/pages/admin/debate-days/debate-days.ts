import { Component, computed, effect, inject, signal } from '@angular/core';
import { errorMessage } from '../../../../../shared/interceptors/error.interceptor';
import { formatearFecha } from '../../../../../shared/utils/format';
import { DebateDaysService } from '../../../services/debate-days.service';

/**
 * Global debate-days administration page (T-090, RF-24, v2.4).
 *
 * Shows the stored integer days (default 30 when never set), validates them
 * (integer 1-90) before saving, stores the new audited value and reloads it
 * (including `updatedBy`/`updatedAt`). The deadline of a debate is fixed at
 * opening, so the note makes clear the setting only applies to the debates
 * opened from then on. Only administrators can reach this page (RNF-7); 422
 * `DEBATE_DAYS_INVALID` problems are surfaced (RNF-3).
 */
@Component({
  selector: 'app-debate-days-page',
  templateUrl: './debate-days.html',
})
export class DebateDaysPage {
  private readonly debateDaysService = inject(DebateDaysService);

  /** The stored value (default 30 when never set). */
  protected readonly dias = this.debateDaysService.dias;

  /** The current draft of the debate days. */
  protected readonly borrador = signal(30);
  /** `true` while the save is in flight. */
  protected readonly guardando = signal(false);
  /** `true` after a successful save. */
  protected readonly guardado = signal(false);
  /** The last backend error message to surface (RNF-3). */
  protected readonly error = signal('');
  /** The 422 `DEBATE_DAYS_INVALID` problems, when the backend rejected the save. */
  protected readonly problemas = signal<string[]>([]);

  private inicializado = false;

  constructor() {
    // Prefills the draft with the stored value once it loads (the first time)
    // so the form shows the persisted days, not the default.
    effect(() => {
      const d = this.dias.value();
      if (d == null || this.inicializado) return;
      this.inicializado = true;
      this.borrador.set(d.debateDays);
    });
  }

  /** The client-side validation message (`''` when the draft is valid). */
  protected readonly mensajeValidacion = computed(() => {
    const n = this.borrador();
    if (!Number.isInteger(n) || n < 1 || n > 90) {
      return 'Los días de debate deben ser un entero entre 1 y 90.';
    }
    return '';
  });

  /** `true` when the form may be saved (client validation passed). */
  protected readonly valido = computed(() => this.mensajeValidacion() === '');

  protected setBorrador(raw: string): void {
    this.borrador.set(raw === '' ? 0 : Number.parseInt(raw, 10));
    this.guardado.set(false);
  }

  /** Stores the validated debate days (RF-24, v2.4). */
  protected guardar(): void {
    if (!this.valido() || this.guardando()) return;
    this.guardando.set(true);
    this.error.set('');
    this.problemas.set([]);
    this.guardado.set(false);
    void this.debateDaysService
      .guardar(this.borrador())
      .then(() => {
        this.guardado.set(true);
        this.dias.reload();
      })
      .catch((err) => {
        this.error.set(errorMessage(err));
        const body = (
          err as { error?: { code?: string; details?: Record<string, unknown> } }
        )?.error;
        if (body?.code === 'DEBATE_DAYS_INVALID') {
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
