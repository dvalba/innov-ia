import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { errorMessage } from '../../../../shared/interceptors/error.interceptor';
import { ThemePicker } from '../../../../shared/components/theme-picker/theme-picker';

/**
 * Forced password change on first access (T-038, RF-17).
 *
 * Shown before any other action when the account is created with a temporary
 * password: it calls `POST /auth/change-password` and, on success, the user
 * is released to the main layout. Messages are in Spanish (RNF-4) and the
 * flow is keyboard operable (labels, `role=alert`, focusable controls).
 */
@Component({
  selector: 'app-change-password',
  imports: [FormsModule, ThemePicker],
  templateUrl: './change-password.html',
  styleUrl: './change-password.css',
})
export class ChangePassword {
  protected readonly currentPassword = signal('');
  protected readonly newPassword = signal('');
  protected readonly confirm = signal('');
  protected readonly loading = signal(false);
  protected readonly error = signal('');

  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  protected get passwordMismatch(): boolean {
    return (
      this.newPassword().length > 0 && this.confirm().length > 0 &&
      this.newPassword() !== this.confirm()
    );
  }

  protected async onSubmit(): Promise<void> {
    this.error.set('');
    if (this.loading()) return;
    if (this.newPassword().length < 6) {
      this.error.set('La nueva contraseña debe tener al menos 6 caracteres.');
      return;
    }
    if (this.newPassword() !== this.confirm()) {
      this.error.set('La confirmación no coincide con la nueva contraseña.');
      return;
    }
    this.loading.set(true);
    try {
      await this.auth.changePassword(this.currentPassword(), this.newPassword());
      void this.router.navigate(['/']);
    } catch (err) {
      this.error.set(errorMessage(err));
    } finally {
      this.loading.set(false);
    }
  }
}
