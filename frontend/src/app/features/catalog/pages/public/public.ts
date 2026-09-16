import { Component } from '@angular/core';

/**
 * Public catalog placeholder (T-004 shell; feature in T-052).
 * UI in Spanish (RNF-4).
 */
@Component({
  selector: 'app-public-catalog',
  template: `
    <div class="rounded-xl border border-slate-200 bg-white p-8">
      <h1 class="text-xl font-semibold text-slate-900">Catálogo público</h1>
      <p class="mt-2 text-sm text-slate-600">
        Aquí verás las iniciativas validadas y publicadas por la comunidad.
      </p>
    </div>
  `,
})
export class PublicCatalog {}
