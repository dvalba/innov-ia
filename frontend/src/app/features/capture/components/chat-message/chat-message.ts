import { Component, input } from '@angular/core';
import { ChatRole } from '../../../../shared/types/models';

/** One row of the client-side capture transcript (T-042, plan §2.3). */
export interface MensajeChat {
  id: string;
  role: ChatRole;
  text: string;
}

/**
 * Chat bubble (T-042, RF-3).
 *
 * Renders a single capture message: the user's bubble on the right, the
 * assistant's on the left and system notes (resumes, contingencies) centered
 * and muted. UI copy arrives already in Spanish (RNF-4).
 */
@Component({
  selector: 'app-chat-message',
  templateUrl: './chat-message.html',
  styleUrl: './chat-message.css',
})
export class ChatMessage {
  /** The message to render. */
  readonly mensaje = input.required<MensajeChat>();
}
