import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';
import { errorMessage } from '../../../../shared/interceptors/error.interceptor';
import { ThemePicker } from '../../../../shared/components/theme-picker/theme-picker';

/**
 * Login screen (T-037, RF-1).
 *
 * Username/password form in Spanish. On failure it shows a single message
 * without revealing which datum was wrong (RF-1). On success the `AuthService`
 * stores the session and navigates to the main layout.
 */
@Component({
  selector: 'app-login',
  imports: [FormsModule, ThemePicker],
  templateUrl: './login.html',
  styleUrl: './login.css',
})
export class Login {
  protected readonly username = signal('');
  protected readonly password = signal('');
  protected readonly loading = signal(false);
  protected readonly error = signal('');

  private readonly auth = inject(AuthService);

  protected async onSubmit(): Promise<void> {
    this.error.set('');
    if (this.loading()) return;
    this.loading.set(true);
    try {
      await this.auth.login(this.username().trim(), this.password());
    } catch (err) {
      this.error.set(errorMessage(err));
    } finally {
      this.loading.set(false);
    }
  }
}
