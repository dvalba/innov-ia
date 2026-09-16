import { Component } from '@angular/core';

/**
 * "Mis ideas" listing placeholder (T-004 shell; feature in T-046).
 * UI in Spanish (RNF-4).
 */
@Component({
  selector: 'app-idea-list',
  template: `
    <div class="rounded-xl border border-slate-200 bg-white p-8">
      <h1 class="text-xl font-semibold text-slate-900">Mis ideas</h1>
      <p class="mt-2 text-sm text-slate-600">
        Aquí verás la lista de tus iniciativas (título, fecha, origen y
        estado).
      </p>
    </div>
  `,
})
export class IdeaList {}
