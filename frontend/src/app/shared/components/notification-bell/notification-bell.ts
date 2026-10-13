import { Component, DestroyRef, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { NotificationsService } from '../../services/notifications.service';
import { formatearFecha } from '../../utils/format';
import { Notificacion } from '../../types/models';

/** How often the bell refreshes the list + unread counter while mounted. */
const POLL_MS = 15_000;

/**
 * Notification bell (T-055, RF-18).
 *
 * Lives in the layout header (shared, no feature imports): a bell button with
 * the unread counter (the live `unread` from the polling `GET /notifications`
 * resource), a dropdown with the messages (Spanish, newest first) and their
 * date, and each item navigates to its object by `ideaId` (the G11 idea
 * detail) and marks it read on consult (`POST /notifications/{id}/read`,
 * recipient-only). Only the four in-app events exist; nothing is emitted here.
 */
@Component({
  selector: 'app-notification-bell',
  templateUrl: './notification-bell.html',
})
export class NotificationBell {
  private readonly notifs = inject(NotificationsService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  /** `GET /notifications` (list + unread counter), refreshed on a timer. */
  protected readonly notificaciones = this.notifs.notificaciones;
  /** Whether the dropdown list is open. */
  protected readonly abierto = signal(false);

  protected readonly formatearFecha = formatearFecha;

  constructor() {
    // Refetch immediately on entry (no-op while the initial load runs): the
    // root-level resource would otherwise keep the previous list cached.
    this.notificaciones.reload();
    // Refresh the list + counter while the bell is mounted (the user is
    // signed in); the timer is cleared on destroy so it never runs afterwards.
    const timer = setInterval(() => this.notificaciones.reload(), POLL_MS);
    this.destroyRef.onDestroy(() => clearInterval(timer));
  }

  protected toggle(): void {
    this.abierto.update((v) => !v);
  }

  protected cerrar(): void {
    this.abierto.set(false);
  }

  protected sinLees(): boolean {
    return (this.notificaciones.value()?.unread ?? 0) === 0;
  }

  /**
   * Marks the notification read and navigates to its object. Owner events
   * (`IDEA_REFINED`/`IDEA_PUBLISHED`/`IDEA_REJECTED`) go to the G11 idea detail
   * by `ideaId`; `IDEA_REQUESTED` is received by the specialist, whose object
   * is the review queue (G12), so it goes to `/validacion`. Navigating by path
   * keeps this shared component free of feature imports.
   */
  protected onConsultar(n: Notificacion): void {
    this.abierto.set(false);
    void this.notifs
      .marcarLeida(n.id)
      .catch(() => void 0)
      .finally(() => this.notifs.notificaciones.reload());
    const destino = n.type === 'IDEA_REQUESTED' ? ['/validacion'] : ['/mis-ideas', n.ideaId];
    void this.router.navigate(destino);
  }
}
