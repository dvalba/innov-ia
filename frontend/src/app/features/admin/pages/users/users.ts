import { Component, inject, signal } from '@angular/core';
import { RoleMatrix } from '../../components/role-matrix/role-matrix';
import { UserForm } from '../../components/user-form/user-form';
import { errorMessage } from '../../../../shared/interceptors/error.interceptor';
import { UsersService, CreatedUser } from '../../services/users.service';
import { Usuario } from '../../../../shared/types/models';
import { roleLabel } from '../../../../shared/utils/roles';

/**
 * Users administration page (T-053/T-054, RF-17).
 *
 * Lists the accounts (username, name, area, contact, roles, state), creates
 * users (the one-time temporary password is shown exactly once, with a copy
 * helper), toggles enabled/disabled and assigns/revokes roles through the
 * role matrix. When the backend rejects an operation (409 username taken,
 * 409 last-administrator rule) the change is not applied and the message is
 * surfaced. Users without roles are flagged "Sin acceso a funciones".
 */
@Component({
  selector: 'app-user-management',
  imports: [UserForm, RoleMatrix],
  template: `
    <div class="space-y-6">
      <header class="rounded-xl border border-slate-200 bg-white p-6">
        <h1 class="text-xl font-semibold text-slate-900">Administración de usuarios</h1>
        <p class="mt-1 text-sm text-slate-500">
          Crea cuentas y habilita o desactiva usuarios. Una cuenta desactivada
          pierde el acceso; sus ideas e historial se conservan.
        </p>
      </header>

      <app-user-form (created)="onCreated($event)" />

      @if (created()) {
        <div
          role="status"
          aria-live="polite"
          class="flex flex-col gap-3 rounded-xl border border-indigo-200 bg-indigo-50 p-4 sm:flex-row sm:items-center sm:justify-between"
        >
          <div class="min-w-0">
            <p class="text-sm font-medium text-indigo-900">
              Usuario <span class="font-semibold">{{ created()!.user.username }}</span> creado.
            </p>
            <p class="mt-1 text-sm text-indigo-900">
              Contraseña temporal — entrégala de inmediato, solo se muestra una vez:
            </p>
            <code
              class="mt-1 inline-block rounded-md bg-white px-3 py-1 font-mono text-base tracking-wider text-indigo-700 ring-1 ring-indigo-200"
              aria-label="Contraseña temporal"
              >{{ created()!.temporaryPassword }}</code
            >
          </div>
          <div class="flex shrink-0 gap-2">
            <button
              type="button"
              (click)="onCopy()"
              class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-300"
            >
              {{ copied() ? '¡Copiada!' : 'Copiar' }}
            </button>
            <button
              type="button"
              (click)="dismissCreated()"
              class="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-300"
            >
              Entendida
            </button>
          </div>
        </div>
      }

      @if (error()) {
        <div
          role="alert"
          class="flex items-start justify-between gap-4 rounded-xl border border-red-200 bg-red-50 p-4"
        >
          <p class="text-sm text-red-700">{{ error() }}</p>
          <button
            type="button"
            (click)="clearError()"
            aria-label="Descartar mensaje"
            class="shrink-0 rounded-lg px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100"
          >
            Cerrar
          </button>
        </div>
      }

      @if (list.isLoading()) {
        <p role="status" class="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
          Cargando usuarios…
        </p>
      } @else {
        @if ((list.value() ?? []).length === 0) {
          <p class="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
            Aún no hay usuarios. Crea el primero con el formulario anterior.
          </p>
        } @else {
          <ul class="space-y-3">
            @for (user of list.value(); track user.id) {
              <li
                class="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-5 lg:flex-row lg:items-center lg:justify-between"
                [class.opacity-75]="!user.active"
              >
                <div class="min-w-0 flex-1 space-y-2">
                  <div class="flex flex-wrap items-center gap-2">
                    <span class="text-base font-semibold text-slate-900">{{ user.username }}</span>
                    <span
                      class="rounded-full px-2.5 py-0.5 text-xs font-medium ring-1"
                      [class]="user.active
                        ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                        : 'bg-slate-100 text-slate-600 ring-slate-200'"
                      >{{ user.active ? 'Habilitado' : 'Desactivado' }}</span
                    >
                  </div>
                  <p class="text-sm text-slate-600">
                    {{ user.name || '—' }}
                    <span class="mx-1.5 text-slate-300">·</span>
                    {{ user.area || '—' }}
                    <span class="mx-1.5 text-slate-300">·</span>
                    {{ user.contact || '—' }}
                  </p>
                  <div class="flex flex-wrap items-center gap-1.5" aria-label="Roles de {{ user.username }}">
                    @if (user.roles.length === 0) {
                      <span
                        class="rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-700 ring-1 ring-amber-200"
                      >
                        Sin acceso a funciones
                      </span>
                    } @else {
                      @for (role of user.roles; track role) {
                        <span
                          class="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-slate-200"
                          >{{ roleLabel(role) }}</span
                        >
                      }
                    }
                  </div>
                  @if (!user.active) {
                    <p class="text-xs text-slate-500">
                      Sin acceso a la plataforma; cuenta, ideas e historial conservados.
                    </p>
                  }
                </div>

                <div class="flex shrink-0 flex-col gap-3 sm:flex-row sm:items-start">
                  <button
                    type="button"
                    (click)="onToggle(user)"
                    [disabled]="togglingId() === user.id"
                    [attr.aria-label]="(user.active ? 'Desactivar' : 'Habilitar') + ' a ' + user.username"
                    class="self-start rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-300 disabled:cursor-not-allowed disabled:opacity-60 sm:self-auto"
                  >
                    {{ togglingId() === user.id
                      ? 'Guardando…'
                      : user.active
                        ? 'Desactivar'
                        : 'Habilitar' }}
                  </button>
                    <app-role-matrix
                      [user]="user"
                      [saving]="rolesSavingId() === user.id"
                    (saveRequested)="onSaveRoles(user, $event)"
                  />
                </div>
              </li>
            }
          </ul>
        }
      }
    </div>
  `,
})
export class UserManagement {
  private readonly users = inject(UsersService);

  protected readonly list = this.users.listUsers;
  protected readonly roleLabel = roleLabel;

  protected readonly created = signal<CreatedUser | null>(null);
  protected readonly copied = signal(false);
  protected readonly error = signal('');
  protected readonly togglingId = signal<string | null>(null);
  protected readonly rolesSavingId = signal<string | null>(null);

  constructor() {
    // Refetch on every entry: the root-level resource keeps its cached list
    // across sessions/users within the same SPA lifecycle.
    this.list.reload();
  }

  protected onCreated(payload: CreatedUser): void {
    this.created.set(payload);
    this.copied.set(false);
    this.list.reload();
  }

  protected async onCopy(): Promise<void> {
    const password = this.created()?.temporaryPassword;
    if (!password) return;
    try {
      await navigator.clipboard.writeText(password);
      this.copied.set(true);
      setTimeout(() => this.copied.set(false), 2000);
    } catch {
      // The clipboard may be unavailable; the value remains visible.
    }
  }

  protected dismissCreated(): void {
    this.created.set(null);
  }

  protected clearError(): void {
    this.error.set('');
  }

  protected async onToggle(user: Usuario): Promise<void> {
    this.error.set('');
    this.togglingId.set(user.id);
    try {
      await this.users.toggleActive(user.id);
      this.list.reload();
    } catch (err) {
      // 409 last-admin (or any rejection): the change was not applied.
      this.error.set(errorMessage(err));
    } finally {
      this.togglingId.set(null);
    }
  }

  protected async onSaveRoles(user: Usuario, roles: string[]): Promise<void> {
    this.error.set('');
    this.rolesSavingId.set(user.id);
    try {
      await this.users.setRoles(user.id, roles);
      this.list.reload();
    } catch (err) {
      // 409 last-admin (or any rejection): the change was not applied.
      this.error.set(errorMessage(err));
    } finally {
      this.rolesSavingId.set(null);
    }
  }
}
