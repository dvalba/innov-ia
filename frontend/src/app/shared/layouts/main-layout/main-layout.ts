import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ROLE_ADMIN, ROLE_PROPOSER, ROLE_VALIDATOR } from '../../types/models';
import { roleLabel } from '../../utils/roles';
import { SessionService } from '../../services/session.service';
import { NotificationBell } from '../../components/notification-bell/notification-bell';

/**
 * Main layout (T-004, plan §1.1, Constitution §3.2).
 *
 * Sidebar + main content. On large screens the sidebar is static; on smaller
 * screens it becomes a slide-in drawer toggled from the header. The header
 * holds the mobile menu toggle, the navigation shortcuts, the settings (gear)
 * entry and the notification bell. The sidebar shows the signed-in user's
 * name, their roles and a "Cerrar sesión" action. The layout only depends on
 * shared services (no feature imports): the logout call is a simple mutation
 * through `HttpClient` and the local state is cleared via `SessionService`.
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

  /** Whether the mobile sidebar drawer is open. */
  protected readonly menuAbierto = signal(false);

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

  protected toggleMenu(): void {
    this.menuAbierto.update((v) => !v);
  }

  protected cerrarMenu(): void {
    this.menuAbierto.set(false);
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
