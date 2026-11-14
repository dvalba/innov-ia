import { Routes } from '@angular/router';

import { ROLE_ADMIN, ROLE_PROPOSER, ROLE_VALIDATOR } from './shared/types/models';
import {
  loginOnly,
  mustChangePasswordOnly,
  requireRole,
  requireSession,
} from './shared/guards/route-guards';

/**
 * Application routes (T-004, plan §1.1).
 *
 * Every feature page is lazy-loaded (`loadComponent`). The shell
 * (`shared/layouts/main-layout`) hosts the protected sections; role guards
 * follow plan §3.1 (RNF-7). `loginOnly` keeps an active session out of
 * `/login`; `requireSession` protects the shell.
 */
export const routes: Routes = [
  {
    path: 'login',
    canActivate: [loginOnly],
    loadComponent: () =>
      import('./features/auth/pages/login/login').then((m) => m.Login),
  },
  {
    // Forced change of the temporary password on first access (T-038, RF-17):
    // only reachable while the account is in the "must change" state.
    path: 'cambiar-contrasena',
    canActivate: [mustChangePasswordOnly],
    loadComponent: () =>
      import('./features/auth/pages/change-password/change-password').then(
        (m) => m.ChangePassword,
      ),
  },
  {
    path: '',
    canActivate: [requireSession],
    loadComponent: () =>
      import('./shared/layouts/main-layout/main-layout').then((m) => m.MainLayout),
    children: [
      {
        path: '',
        pathMatch: 'full',
        loadComponent: () =>
          import('./shared/pages/home/home').then((m) => m.Home),
      },
      {
        path: 'captura',
        canActivate: [requireRole(ROLE_PROPOSER)],
        children: [
          {
            path: '',
            loadComponent: () =>
              import('./features/capture/pages/new-idea/new-idea').then(
                m => m.NewIdea,
              ),
          },
          {
            path: 'chat-assist',
            loadComponent: () =>
              import('./features/capture/pages/chat-assist/chat-assist').then(
                (m) => m.ChatAssist,
              ),
          },
          {
            path: 'manual',
            loadComponent: () =>
              import('./features/capture/pages/manual/manual').then(
                (m) => m.ManualIdea,
              ),
          },
        ],
      },
      {
        path: 'mis-ideas',
        canActivate: [requireRole(ROLE_PROPOSER)],
        children: [
          {
            path: '',
            loadComponent: () =>
              import('./features/my-ideas/pages/list/list').then(
                (m) => m.IdeaList,
              ),
          },
          {
            path: ':id',
            loadComponent: () =>
              import('./features/my-ideas/pages/detail/detail').then(
                (m) => m.IdeaDetail,
              ),
          },
        ],
      },
      {
        path: 'validacion',
        canActivate: [requireRole(ROLE_VALIDATOR)],
        children: [
          {
            path: '',
            loadComponent: () =>
              import('./features/validation/pages/queue/queue').then(
                (m) => m.ReviewQueue,
              ),
          },
        ],
      },
      {
        path: 'catalogo',
        children: [
          {
            path: '',
            pathMatch: 'full',
            redirectTo: 'publico',
          },
          {
            path: 'publico',
            loadComponent: () =>
              import('./features/catalog/pages/public/public').then(
                (m) => m.PublicCatalog,
              ),
          },
          {
            path: 'publico/:id',
            loadComponent: () =>
              import('./features/catalog/pages/detail/detail').then(
                (m) => m.CatalogDetail,
              ),
          },
          {
            // Read-only full debate thread (T-085, RF-24): target of the
            // compact closure box "Ver el debate completo" link.
            path: 'publico/:id/debate',
            loadComponent: () =>
              import('./features/catalog/pages/debate-readonly/debate-readonly').then(
                (m) => m.DebateReadonly,
              ),
          },
        ],
      },
      {
        path: 'admin',
        canActivate: [requireRole(ROLE_ADMIN)],
        loadComponent: () =>
          import('./features/admin/pages/admin/admin').then((m) => m.AdminShell),
        children: [
          {
            path: '',
            pathMatch: 'full',
            loadComponent: () =>
              import('./features/admin/pages/users/users').then(
                (m) => m.UserManagement,
              ),
          },
          {
            path: 'contexto',
            loadComponent: () =>
              import('./features/admin/pages/admin/contexto/contexto').then(
                (m) => m.ContextoPage,
              ),
          },
          {
            path: 'umbrales',
            loadComponent: () =>
              import('./features/admin/pages/admin/umbrales/umbrales').then(
                (m) => m.UmbralesPage,
              ),
          },
          {
            path: 'debate-dias',
            loadComponent: () =>
              import('./features/admin/pages/admin/debate-days/debate-days').then(
                (m) => m.DebateDaysPage,
              ),
          },
        ],
      },
      {
        path: 'ajustes',
        loadComponent: () =>
          import('./shared/pages/settings/settings').then((m) => m.Settings),
      },
      { path: '**', redirectTo: '' },
    ],
  },
];
