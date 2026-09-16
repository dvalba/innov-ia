import { Component } from '@angular/core';

/**
 * Validation queue placeholder (T-004 shell; feature in T-051).
 * UI in Spanish (RNF-4).
 */
@Component({
  selector: 'app-review-queue',
  template: `
    <div class="rounded-xl border border-slate-200 bg-white p-8">
      <h1 class="text-xl font-semibold text-slate-900">Validación de ideas</h1>
      <p class="mt-2 text-sm text-slate-600">
        Aquí verás la cola de iniciativas en solicitud de publicación y podrás
        validarlas o rechazarlas con comentario.
      </p>
    </div>
  `,
})
export class ReviewQueue {}
