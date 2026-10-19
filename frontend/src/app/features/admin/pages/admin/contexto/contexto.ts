import { Component } from '@angular/core';
import { ContextoPanel } from '../../../components/contexto-panel/contexto-panel';

/**
 * Company-context administration page (T-076, RF-21).
 *
 * Hosts the `ContextoPanel` (template download, online editor and file
 * upload) inside the `/admin` shell, reachable only by administrators.
 */
@Component({
  selector: 'app-contexto-page',
  imports: [ContextoPanel],
  template: `
    <header class="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900 sm:p-6">
      <h1 class="text-xl font-semibold text-slate-900 dark:text-slate-100">Contexto de empresa</h1>
      <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Documento único que la IA usa como referencia en todas sus operaciones. Éditalo en línea, descarga la
        plantilla o sube un archivo para sustituirlo por completo.
      </p>
    </header>

    <app-contexto-panel />
  `,
})
export class ContextoPage {}
