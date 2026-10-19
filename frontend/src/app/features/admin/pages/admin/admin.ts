import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

/**
 * Administration shell (T-076, RF-21/RF-17).
 *
 * The `/admin` entry point (administrator role) hosts the section tabs —
 * Users and Company context — with a `<router-outlet>` that renders the
 * active section (users by default, the context section at
 * `/admin/contexto`, both lazy-loaded through the child routes).
 */
@Component({
  selector: 'app-admin',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './admin.html',
})
export class AdminShell {}
