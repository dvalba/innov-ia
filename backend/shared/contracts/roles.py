"""Shared role contract between features (T-021, RF-10/RF-15/RF-16).

Resolves the `ideas` <-> `users` coupling (Constitution §4.2 / §4.3): the
`ideas` feature must check the specialist role and fan out
`IDEA_REQUESTED` to all specialists WITHOUT importing `features.users`.
Reference role values are the spec contracts mirrored from the users domain.
"""

ROLE_PROPOSER = "proponente"
ROLE_SPECIALIST = "especialista"
ROLE_ADMIN = "admin"

KNOWN_ROLES: tuple[str, ...] = (ROLE_PROPOSER, ROLE_SPECIALIST, ROLE_ADMIN)


def list_specialists(directory) -> list[str]:
    """Ids of every active user holding the specialist role (fanout target set, RF-18).

    Receives any `UserDirectory`-shaped collaborator injected by the caller
    (plan §1.2 coupling note); it never imports another feature.
    """
    return [
        user["id"]
        for user in directory.list()
        if ROLE_SPECIALIST in user.get("roles", ()) and user.get("active", True)
    ]
