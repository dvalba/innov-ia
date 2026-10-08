import { HttpClient, httpResource } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { Notificacion, NotificacionListado } from '../types/models';

/**
 * Notification center API client (T-055, RF-18).
 *
 * Read side: the `GET /notifications` resource (list + unread counter). The
 * list is reloaded by the consumer on a timer (the bell, scoped to the active
 * session) so polling never runs without one. The `mark-read` mutation
 * (`POST /notifications/{id}/read`, recipient-only) is encapsulated with
 * `HttpClient` (guideline §5). It only consumes the `notifications` (G10)
 * contracts — it never changes them (RNF-2).
 */
@Injectable({ providedIn: 'root' })
export class NotificationsService {
  private readonly http = inject(HttpClient);

  /** GET /notifications -> `{ notifications, unread }` (newest first). */
  readonly notificaciones = httpResource<NotificacionListado>(() => '/notifications');

  /** POST /notifications/{id}/read — mark one read (recipient-only, RF-18). */
  marcarLeida(notificationId: string): Promise<Notificacion> {
    return firstValueFrom(
      this.http.post<Notificacion>(`/notifications/${notificationId}/read`, null),
    );
  }
}
