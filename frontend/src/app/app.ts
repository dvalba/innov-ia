import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

/**
 * Application root (T-004, plan §1.1).
 *
 * The shell is just a router outlet: the login screen and the main layout
 * (with its own sidebar) are rendered by the lazy routes in `app.routes.ts`.
 */
@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  template: '<router-outlet />',
})
export class App {}
