import { Component } from '@angular/core';

/**
 * "New idea" entry page placeholder (T-004 shell; feature in T-041/T-042).
 * UI in Spanish (RNF-4).
 */
@Component({
  selector: 'app-new-idea',
  template: `
    <div class="rounded-xl border border-slate-200 bg-white p-8">
      <h1 class="text-xl font-semibold text-slate-900">Nueva idea</h1>
      <p class="mt-2 text-sm text-slate-600">
        Aquí iniciarás la captura de una nueva iniciativa (asistida por el
        asistente o manual).
      </p>
    </div>
  `,
})
export class NewIdea {}
