import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { SessionService } from '../services/session.service';

/**
 * Route guards (T-039, RF-1, RNF-7).
 *
 * - `requireSession`: blocks protected routes while there is no active
 *   session (redirects to `/login`).
 * - `loginOnly`: keeps an already-authenticated user out of `/login`.
 * - `requireRole(...roles)`: guards a route by role; a session without the
 *   role is redirected back to the layout home.
 */

export const requireSession: CanActivateFn = () => {
  const session = inject(SessionService);
  const router = inject(Router);
  return session.sesionActiva() ? true : router.createUrlTree(['/login']);
};

export const loginOnly: CanActivateFn = () => {
  const session = inject(SessionService);
  const router = inject(Router);
  return session.sesionActiva() ? router.createUrlTree(['/']) : true;
};

export const requireRole =
  (...roles: string[]): CanActivateFn =>
  () => {
    const session = inject(SessionService);
    const router = inject(Router);
    if (!session.sesionActiva()) return router.createUrlTree(['/login']);
    if (roles.length > 0 && !session.tieneRol(...roles)) return router.createUrlTree(['/']);
    return true;
  };
