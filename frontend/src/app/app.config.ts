import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideRouter } from '@angular/router';

import { routes } from './app.routes';
import { authInterceptor } from './shared/interceptors/auth.interceptor';
import { errorInterceptor } from './shared/interceptors/error.interceptor';

/**
 * App configuration (T-004/T-005, plan §1.1).
 *
 * Router with the lazy routes of `app.routes.ts` and `HttpClient` with the
 * shared interceptors: `authInterceptor` (bearer token, 401 → /login) first,
 * then `errorInterceptor` which normalizes error bodies (plan §3.6).
 */
export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(withInterceptors([authInterceptor, errorInterceptor])),
  ],
};
