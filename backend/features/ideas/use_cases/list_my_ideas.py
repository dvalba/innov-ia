"""List "Mis ideas" use case (T-022, RF-19, RNF-7).

Returns the listing the user needs to consult their own initiatives:
title, registration date, origin and state, in any state (the idea keeps
operating normally while the refinement is pending, RF-11). Only the ideas
of the requesting user are ever returned (RNF-7: every role sees only its
own data); the entry's `id` is what "open any of them" (RF-19) feeds into
the detail endpoint.
"""

from features.ideas.infrastructure.idea_store import IdeaStore


def list_my_ideas(ledger: IdeaStore, *, owner_id: str) -> list[dict]:
    """Lists the ideas of `owner_id` (any state), newest first.

    Each entry holds the RF-19 summary: `id`, `title`, `createdAt`,
    `origin`, `state`. Ideas of other users never appear (RNF-7), and a
    user without ideas gets an empty list.
    """
    entries = [
        {
            "id": payload["id"],
            "title": payload["title"],
            "createdAt": payload["createdAt"],
            "origin": payload["origin"],
            "state": payload["state"],
        }
        for payload in ledger.list()
        if payload["ownerId"] == owner_id
    ]
    entries.sort(key=lambda entry: (entry["createdAt"], entry["id"]), reverse=True)
    return entries
