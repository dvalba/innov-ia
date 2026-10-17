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
      <div class="max-w-2xl rounded-xl border border-slate-200 bg-white p-6 sm:p-8 dark:border-slate-700 dark:bg-slate-900">
        <h1 class="text-xl font-semibold text-slate-900 dark:text-slate-100">Bienvenido a Innov-IA</h1>
        <p class="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Plataforma inteligente para la captura, estructuración y evaluación de
          iniciativas de innovación.
        </p>
        <p class="mt-4 text-sm text-slate-500 dark:text-slate-400">
          Usa el menú lateral para navegar: Mis ideas, Catálogo, Nueva idea o
          Administración. El icono de engranaje abre los ajustes de la
          apariencia.
        </p>
      </div>
  `,
})
export class Home {}
