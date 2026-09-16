import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { SessionService } from '../services/session.service';

/**
 * Endpoints that legitimately return 401 for user-input reasons while the
 * user is on an auth screen; a 401 there must NOT clear the session or
 * redirect (the screen shows the message instead).
 */
function isAuthInputEndpoint(url: string | undefined): boolean {
  if (!url) return false;
  return /\/auth\/login$|\/auth\/change-password$/.test(url);
}

/**
 * Auth interceptor (T-005, RF-1, RNF-7).
 *
 * Injects the bearer token on every request while a session is active, and,
 * on any 401 for a protected endpoint, clears the session and redirects to
 * `/login`.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const session = inject(SessionService);
  const router = inject(Router);

  const token = session.token();
  const request = token
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  let hasNavigated = false;

  return next(request).pipe(
    catchError((error) => {
      const status: number | undefined = error?.status;
      const url: string | undefined = error?.url;
      if (status === 401 && !isAuthInputEndpoint(url) && !hasNavigated) {
        hasNavigated = true;
        session.cerrar();
        void router.navigate(['/login']);
      }
      return throwError(() => error);
    })
  );
};
