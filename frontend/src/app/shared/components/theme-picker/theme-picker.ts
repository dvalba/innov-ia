import { Component, inject } from '@angular/core';
import { ThemePreference, ThemeService } from '../../services/theme.service';

/**
 * Compact theme picker (light / dark / system).
 *
 * Shared segmented control used where there is no settings entry point
 * (standalone auth screens) so the appearance preference stays reachable
 * everywhere; the settings view uses the expanded layout.
 */
@Component({
  selector: 'app-theme-picker',
  template: `
    <div
      class="inline-flex items-center rounded-lg border border-slate-200 p-0.5 dark:border-slate-700"
      role="group"
      aria-label="Tema de la interfaz"
    >
      @for (opt of opciones; track opt.value) {
        <button
          type="button"
          (click)="elegir(opt.value)"
          [attr.aria-pressed]="tema() === opt.value"
          [class]="
            'rounded-md px-2.5 py-1 text-xs font-medium transition focus:outline-none focus:ring-2 focus:ring-indigo-300 ' +
            (tema() === opt.value
              ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300'
              : 'text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800')
          "
        >
          {{ opt.label }}
        </button>
      }
    </div>
  `,
})
export class ThemePicker {
  protected readonly themeService = inject(ThemeService);
  protected readonly tema = this.themeService.theme;

  protected readonly opciones: Array<{ value: ThemePreference; label: string }> = [
    { value: 'light', label: 'Claro' },
    { value: 'dark', label: 'Oscuro' },
    { value: 'system', label: 'Sistema' },
  ];

  protected elegir(pref: ThemePreference): void {
    this.themeService.setTheme(pref);
  }
}
