import { Component } from '@angular/core';

/**
 * Home page (T-004, shell).
 *
 * Landing inside the main layout while the feature pages of later groups are
 * not implemented yet. UI in Spanish (RNF-4).
 */
@Component({
  selector: 'app-home',
  template: `
    <div class="rounded-xl border border-slate-200 bg-white p-8">
      <h1 class="text-xl font-semibold text-slate-900">Bienvenido a Innov-IA</h1>
      <p class="mt-2 text-sm text-slate-600">
        Plataforma inteligente para la captura, estructuración y evaluación de
        iniciativas de innovación.
      </p>
      <p class="mt-4 text-sm text-slate-500">
        Usa el menú lateral para navegar: Mis ideas, Catálogo, Nueva idea o
        Administración.
      </p>
    </div>
  `,
})
export class Home {}
