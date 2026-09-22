import { HttpClient, httpResource } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { Usuario } from '../../../shared/types/models';

/** `POST /users` (201) payload: public user + one-time temporary password. */
export interface CreatedUser {
  user: Usuario;
  temporaryPassword: string;
}

/**
 * Users API client (T-053, RF-17).
 *
 * Reads go through `httpResource`; mutations go through the dedicated
 * `HttpClient` per the Angular guidelines (§5). Errors are rethrown so the
 * panel can surface the backend message (400 unknown role, 409 username
 * taken / last-administrator rule).
 */
@Injectable({ providedIn: 'root' })
export class UsersService {
  private readonly http = inject(HttpClient);

  /** GET /users — reactive list for the panel. */
  readonly listUsers = httpResource<Usuario[]>(() => '/users');

  /** POST /users — creates the account; the temporary password is returned once. */
  createUser(payload: { username: string; name: string; area: string; contact: string }): Promise<CreatedUser> {
    return firstValueFrom(this.http.post<CreatedUser>('/users', payload));
  }

  /** PATCH /users/{id}/active — toggles the enabled/disabled flag. */
  toggleActive(userId: string): Promise<Usuario> {
    return firstValueFrom(this.http.patch<Usuario>(`/users/${userId}/active`, null));
  }

  /** PUT /users/{id}/roles — replaces the user's roles (T-054). */
  setRoles(userId: string, roles: string[]): Promise<Usuario> {
    return firstValueFrom(this.http.put<Usuario>(`/users/${userId}/roles`, { roles }));
  }
}
