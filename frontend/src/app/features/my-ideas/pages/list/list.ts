import { Component, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { BadgeState } from '../../../../shared/components/badge-state/badge-state';
import { MyIdeasService } from '../../services/my-ideas.service';
import { origenLabel } from '../../services/my-idea-fields';
import { formatearDia } from '../../../../shared/utils/format';

/**
 * "Mis ideas" listing (T-046, RF-19).
 *
 * Lists the proponent's own ideas — title, registration date, origin and state
 * (with `badge-state`) — via `httpResource` (`GET /ideas/me`), newest first
 * (the backend orders them). Any of them can be opened into the detail page.
 * When there are no ideas, a Spanish empty state is shown.
 */
@Component({
  selector: 'app-idea-list',
  imports: [RouterLink, BadgeState],
  templateUrl: './list.html',
})
export class IdeaList {
  private readonly ideas = inject(MyIdeasService);

  /** `GET /ideas/me` — the proponent's own ideas, newest first. */
  protected readonly miLista = this.ideas.miLista;
  protected readonly origenLabel = origenLabel;
  protected readonly formatearDia = formatearDia;
}
