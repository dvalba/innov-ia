import { Component } from '@angular/core';

/**
 * Idea detail placeholder (T-004 shell; feature in T-047).
 * UI in Spanish (RNF-4).
 */
@Component({
  selector: 'app-idea-detail',
  template: `
    <div class="rounded-xl border border-slate-200 bg-white p-8">
      <h1 class="text-xl font-semibold text-slate-900">Detalle de la idea</h1>
      <p class="mt-2 text-sm text-slate-600">
        Aquí verás y editarás los campos de la idea, y aplicarás las acciones
        disponibles según su estado.
      </p>
    </div>
  `,
})
export class IdeaDetail {}
