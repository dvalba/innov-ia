import { Component, inject, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { errorMessage } from '../../../../shared/interceptors/error.interceptor';
import { UsersService, CreatedUser } from '../../services/users.service';

/**
 * User creation form (T-053, RF-17).
 *
 * Asks for username, name, area and contact (roles are managed in the role
 * matrix). On a 201 the one-time temporary password is handed to the parent
 * through `created` so the panel can show it exactly once. After a successful
 * creation the form resets (a newly created account must never be displayed
 * again).
 */
@Component({
  selector: 'app-user-form',
  imports: [FormsModule],
  templateUrl: './user-form.html',
  styleUrl: './user-form.css',
})
export class UserForm {
  /** Emits the 201 payload (user + temporary password) after a creation. */
  readonly created = output<CreatedUser>();

  protected readonly username = signal('');
  protected readonly name = signal('');
  protected readonly area = signal('');
  protected readonly contact = signal('');
  protected readonly loading = signal(false);
  protected readonly error = signal('');

  private readonly users = inject(UsersService);

  protected reset(): void {
    this.username.set('');
    this.name.set('');
    this.area.set('');
    this.contact.set('');
    this.error.set('');
  }

  protected async onSubmit(): Promise<void> {
    this.error.set('');
    if (this.loading() || !this.username().trim()) return;
    this.loading.set(true);
    try {
      const created = await this.users.createUser({
        username: this.username().trim(),
        name: this.name().trim(),
        area: this.area().trim(),
        contact: this.contact().trim(),
      });
      this.created.emit(created);
      this.reset();
    } catch (err) {
      this.error.set(errorMessage(err));
    } finally {
      this.loading.set(false);
    }
  }
}
