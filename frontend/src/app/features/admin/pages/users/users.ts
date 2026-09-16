import { Component } from '@angular/core';

/**
 * User management placeholder (T-004 shell; feature in T-053/T-054).
 * UI in Spanish (RNF-4).
 */
@Component({
  selector: 'app-user-management',
  template: `
    <div class="rounded-xl border border-slate-200 bg-white p-8">
      <h1 class="text-xl font-semibold text-slate-900">Administración de usuarios</h1>
      <p class="mt-2 text-sm text-slate-600">
        Aquí gestionarás los usuarios de la plataforma: creación, roles,
        habilitación y desactivación.
      </p>
    </div>
  `,
})
export class UserManagement {}
