import { Component, inject } from '@angular/core';
import { SessionService } from '../../services/session.service';
import { roleLabel } from '../../utils/roles';
import { ThemePreference, ThemeService } from '../../services/theme.service';

/**
 * Settings page (theme + account summary).
 *
 * Lets the signed-in user pick the appearance (`light` / `dark` / `system`,
 * persisted by `ThemeService`) and shows a read-only summary of the account.
 * UI in Spanish (RNF-4).
 */
@Component({
  selector: 'app-settings',
  template: `
    <div
      class="mx-auto w-full max-w-2xl space-y-6"
    >
      <div>
        <h1 class="text-xl font-semibold text-slate-900 dark:text-slate-100">
          Ajustes
        </h1>
        <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Personaliza la apariencia y consulta los datos de tu cuenta.
        </p>
      </div>

      <section
        class="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
      >
        <h2
          class="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"
        >
          Apariencia
        </h2>
        <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
          El tema se guarda en este navegador.
        </p>
        <div class="mt-4 grid gap-3 sm:grid-cols-3">
          @for (opt of opciones; track opt.value) {
            <button
              type="button"
              (click)="elegirTema(opt.value)"
              [class]="
                'rounded-lg border p-3 text-left transition focus:outline-none focus:ring-2 focus:ring-indigo-300 ' +
                tema() === opt.value
                  ? 'border-indigo-500 bg-indigo-50 dark:border-indigo-400 dark:bg-indigo-950'
                  : 'border-slate-200 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800'
              "
            >
              <span class="flex items-center gap-2">
                @if (topicos[opt.value]) {
                  <span class="flex h-8 w-8 items-center justify-center rounded-md bg-slate-100 text-base text-slate-500 dark:bg-slate-800 dark:text-slate-300">{{
                    topicos[opt.value]
                  }}</span>
                }
              </span>
              <span
                class="mt-2 block text-sm font-medium"
                [class]="
                  tema() === opt.value
                    ? 'text-indigo-700 dark:text-indigo-300'
                    : 'text-slate-700 dark:text-slate-200'
                "
                >{{ opt.label }}</span
              >
              <span
                class="mt-0.5 block text-xs"
                [class]="
                  tema() === opt.value
                    ? 'text-indigo-600/70 dark:text-indigo-300/70'
                    : 'text-slate-400 dark:text-slate-500'
                "
                >{{ opt.hint }}</span
              >
            </button>
          }
        </div>
      </section>

      <section
        class="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
      >
        <h2
          class="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"
        >
          Cuenta
        </h2>
        @if (session.usuario(); as user) {
          <dl class="mt-4 divide-y divide-slate-100 text-sm dark:divide-slate-800">
            <div class="flex gap-4 py-2">
              <dt
                class="w-32 shrink-0 text-slate-500 dark:text-slate-400"
                >Nombre</dt
              >
              <dd class="text-slate-800 dark:text-slate-200">{{ user.name }}</dd>
            </div>
            <div class="flex gap-4 py-2">
              <dt
                class="w-32 shrink-0 text-slate-500 dark:text-slate-400"
                >Usuario</dt
              >
              <dd class="text-slate-800 dark:text-slate-200">{{
                user.username
              }}</dd>
            </div>
            <div class="flex gap-4 py-2">
              <dt
                class="w-32 shrink-0 text-slate-500 dark:text-slate-400"
                >Área</dt
              >
              <dd class="text-slate-800 dark:text-slate-200">{{ user.area }}</dd>
            </div>
            <div class="flex gap-4 py-2">
              <dt
                class="w-32 shrink-0 text-slate-500 dark:text-slate-400"
                >Contacto</dt
              >
              <dd class="text-slate-800 dark:text-slate-200">{{
                user.contact
              }}</dd>
            </div>
            <div class="flex gap-4 py-2">
              <dt
                class="w-32 shrink-0 text-slate-500 dark:text-slate-400"
                >Roles</dt
              >
              <dd>
                <div class="flex flex-wrap gap-1">
                  @for (role of user.roles; track role) {
                    <span
                      class="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                      >{{ roleLabel(role) }}</span
                    >
                  }
                </div>
              </dd>
            </div>
          </dl>
        }
      </section>
    </div>
  `,
})
export class Settings {
  protected readonly session = inject(SessionService);
  protected readonly themeService = inject(ThemeService);
  protected readonly tema = this.themeService.theme;
  protected readonly roleLabel = roleLabel;

  protected readonly opciones: Array<{
    value: ThemePreference;
    label: string;
    hint: string;
  }> = [
    { value: 'light', label: 'Claro', hint: 'Siempre tema claro' },
    { value: 'dark', label: 'Oscuro', hint: 'Siempre tema oscuro' },
    { value: 'system', label: 'Sistema', hint: 'Sigue el sistema operativo' },
  ];

  /** Simple visual mark per option (no icons in the stack). */
  protected readonly topicos: Record<ThemePreference, string> = {
    light: '☀',
    dark: '●',
    system: '◐',
  };

  protected elegirTema(pref: ThemePreference): void {
    this.themeService.setTheme(pref);
  }
}
