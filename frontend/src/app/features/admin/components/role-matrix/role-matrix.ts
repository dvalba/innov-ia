import { Component, input, output, linkedSignal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ROLE_OPCIONES } from '../../../../shared/utils/roles';
import { Usuario } from '../../../../shared/types/models';

/**
 * Role matrix for a single user (T-054, RF-17).
 *
 * Assigns/revokes any combination of the three roles against
 * `PUT /users/{id}/roles`. Saving replaces the full role set. The selection
 * is a `linkedSignal` over the user's persisted roles, so when the parent
 * refreshes the list after a rejection (409 last-administrator rule) the UI
 * reverts to the saved state. The business rules themselves are the
 * backend's: the UI only reflects its state and surfaces its errors.
 */
@Component({
  selector: 'app-role-matrix',
  imports: [FormsModule],
  templateUrl: './role-matrix.html',
  styleUrl: './role-matrix.css',
})
export class RoleMatrix {
  /** The user whose roles are being edited. */
  readonly user = input.required<Usuario>();
  /** True while the parent persists the change. */
  readonly saving = input(false);

  /** Emitted with the new role set to be persisted. */
  readonly saveRequested = output<string[]>();

  protected readonly ROLE_OPCIONES = ROLE_OPCIONES;

  protected readonly selected = linkedSignal<string[]>(() => [...this.user().roles]);

  protected hasRole(role: string): boolean {
    return this.selected().includes(role);
  }

  protected toggle(role: string): void {
    const next = [...this.selected()];
    const index = next.indexOf(role);
    if (index >= 0) {
      next.splice(index, 1);
    } else {
      next.push(role);
    }
    this.selected.set(next);
  }

  protected submit(): void {
    this.saveRequested.emit(this.selected());
  }
}
