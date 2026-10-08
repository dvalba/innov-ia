import { HttpClient } from '@angular/common/http';
import { Component, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ROLE_ADMIN, ROLE_PROPOSER, ROLE_VALIDATOR } from '../../types/models';
import { SessionService } from '../../services/session.service';
import { NotificationBell } from '../../components/notification-bell/notification-bell';

/** Friendly label for a role (UI in Spanish, RNF-4). */
function roleLabel(role: string): string {
  if (role === ROLE_ADMIN) return 'Administrador';
  if (role === ROLE_VALIDATOR) return 'Especialista';
  if (role === ROLE_PROPOSER) return 'Proponente';
  return role;
}

/**
 * Main layout (T-004, plan §1.1, Constitution §3.2).
 *
 * Sidebar + main content. The sidebar shows the signed-in user's name and
 * their roles and a "Cerrar sesión" action. The layout only depends on shared
 * services (no feature imports): the logout call is a simple mutation through
 * `HttpClient` and the local state is cleared via `SessionService`.
 */
@Component({
  selector: 'app-main-layout',
  imports: [RouterLink, RouterLinkActive, RouterOutlet, NotificationBell],
  templateUrl: './main-layout.html',
  styleUrl: './main-layout.css',
})
export class MainLayout {
  protected readonly session = inject(SessionService);
  protected readonly roleLabel = roleLabel;

  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  protected get displayName(): string {
    const user = this.session.usuario();
    return user?.name?.trim() || user?.username || '—';
  }

  protected get initial(): string {
    const name = (this.session.usuario()?.name || this.session.usuario()?.username || '').trim();
    return name.charAt(0).toUpperCase();
  }

  protected get isProposer(): boolean {
    return this.session.roles().includes(ROLE_PROPOSER);
  }

  protected get isValidator(): boolean {
    return this.session.roles().includes(ROLE_VALIDATOR);
  }

  protected get isAdmin(): boolean {
    return this.session.roles().includes(ROLE_ADMIN);
  }

  protected async onLogout(): Promise<void> {
    try {
      await firstValueFrom(this.http.post('/auth/logout', null));
    } catch {
      // Even if the request fails we clear the local session and redirect.
    }
    this.session.cerrar();
    void this.router.navigate(['/login']);
  }
}
