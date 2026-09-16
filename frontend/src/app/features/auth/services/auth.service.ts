import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { SessionService } from '../../../shared/services/session.service';
import { Usuario } from '../../../shared/types/models';

/**
 * Auth service (T-037, RF-1, RF-17).
 *
 * Encapsulates the HTTP communication for the auth endpoints and stores the
 * resulting session in the shared `SessionService`. The `HttpClient` lives
 * here only, per the Angular guidelines.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly session = inject(SessionService);
  private readonly router = inject(Router);

  /** POST /auth/login — stores the session on success and redirects home. */
  async login(username: string, password: string): Promise<void> {
    const response = await firstValueFrom(
      this.http.post<{ token: string; user: Usuario; mustChangePassword?: boolean }>(
        '/auth/login',
        { username, password },
      ),
    );
    this.session.iniciar(response.token, response.user, response.mustChangePassword ?? false);
    // If the account must change the password, the guard keeps it on /change-password.
    if (this.session.mustChangePassword()) {
      void this.router.navigate(['/cambiar-contrasena']);
    } else {
      void this.router.navigate(['/']);
    }
  }

  /** POST /auth/logout — clears the session and returns to /login. */
  async logout(): Promise<void> {
    try {
      await firstValueFrom(this.http.post('/auth/logout', null));
    } catch {
      // Even if the request fails we clear the local session and redirect.
    }
    this.session.cerrar();
    void this.router.navigate(['/login']);
  }

  /** POST /auth/change-password — used by the forced-change dialog (T-038). */
  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await firstValueFrom(this.http.post('/auth/change-password', {
      currentPassword,
      newPassword,
    }));
    this.session.mustChangePassword.set(false);
  }
}
