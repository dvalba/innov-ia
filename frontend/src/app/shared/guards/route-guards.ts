import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { SessionService } from '../services/session.service';

/**
 * Route guards (T-039, RF-1, RNF-7 + T-038 forced change).
 *
 * - `requireSession`: blocks protected routes while there is no active
 *   session (redirects to `/login`).
 * - `loginOnly`: keeps an already-authenticated user out of `/login` (an
 *   account in forced-change state is sent to the change screen).
 * - `requireRole(...roles)`: guards a route by role; a session without the
 *   role is redirected back to the layout home.
 * - `requireNoForcedChange`: while the account must change its (temporary)
 *   password, every other route redirects to `/cambiar-contrasena`; the
 *   change screen itself (`mustChangePasswordOnly`) is the only reachable
 *   page in that state.
 */

export const requireSession: CanActivateFn = () => {
  const session = inject(SessionService);
  const router = inject(Router);
  if (!session.sesionActiva()) return router.createUrlTree(['/login']);
  if (session.mustChangePassword()) return router.createUrlTree(['/cambiar-contrasena']);
  return true;
};

export const loginOnly: CanActivateFn = () => {
  const session = inject(SessionService);
  const router = inject(Router);
  if (!session.sesionActiva()) return true;
  return session.mustChangePassword()
    ? router.createUrlTree(['/cambiar-contrasena'])
    : router.createUrlTree(['/']);
};

export const requireRole =
  (...roles: string[]): CanActivateFn =>
  () => {
    const session = inject(SessionService);
    const router = inject(Router);
    if (!session.sesionActiva()) return router.createUrlTree(['/login']);
    if (session.mustChangePassword()) return router.createUrlTree(['/cambiar-contrasena']);
    if (roles.length > 0 && !session.tieneRol(...roles)) return router.createUrlTree(['/']);
    return true;
  };

/** Active session that must change its password (otherwise redirects home). */
export const mustChangePasswordOnly: CanActivateFn = () => {
  const session = inject(SessionService);
  const router = inject(Router);
  if (!session.sesionActiva()) return router.createUrlTree(['/login']);
  return session.mustChangePassword() ? true : router.createUrlTree(['/']);
};
