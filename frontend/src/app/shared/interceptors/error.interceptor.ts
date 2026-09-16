import { HttpInterceptorFn } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';

/** The unified error contract (plan §3.6). */
export interface InnovErrorBody {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
}

/** Extracts a human message (Spanish) from a backend error response. */
export function errorMessage(error: unknown): string {
  const body = (error as { error?: { message?: string } } | undefined)?.error;
  const message = body?.message;
  return typeof message === 'string' && message ? message : 'Ocurrió un error inesperado.';
}

/**
 * Error interceptor (T-005, plan §3.6).
 *
 * Normalizes any error response to the unified shape
 * `{ error: { code, message, details } }` so consumers can rely on a single
 * contract, then rethrows it so screens can display the message.
 */
export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req).pipe(
    catchError((error) => {
      const raw = error?.error as Partial<InnovErrorBody> | undefined;
      const unified: InnovErrorBody = {
        error: {
          code: raw?.error?.code ?? 'SIN_CODIGO',
          message: raw?.error?.message ?? errorMessage(error),
          details: raw?.error?.details ?? {},
        },
      };
      const normalized = {
        ...error,
        error: unified,
      };
      return throwError(() => normalized as typeof error);
    })
  );
};
