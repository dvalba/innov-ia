"""Users domain: the `Usuario` account entity and known roles (T-014, RF-17).

Pure domain: no FastAPI/Pydantic. Role names are spec contracts (Spanish)
and are shared with the frontend through the documented payload keys.
"""

from dataclasses import dataclass, field
from datetime import datetime

from shared.contracts.roles import KNOWN_ROLES, ROLE_ADMIN, ROLE_SPECIALIST
from shared.exceptions.handlers import DomainError

# Known roles (spec §5 roles / plan §3.1 endpoint tables). A user without
# roles cannot access the platform functions (RF-17). The reference values
# are the shared role contract consumed by the whole platform (T-021).
ROLE_VALIDATOR = ROLE_SPECIALIST


class UnknownRole(DomainError):
    """A role outside the known set was provided (400)."""

    def __init__(self, role: str) -> None:
        super().__init__("UNKNOWN_ROLE",
                         f"Rol desconocido: «{role}».",
                         status_code=400)


@dataclass
class Usuario:
    """A user account (plan §2.1 `User`, RF-17).

    `roles` is validated against the known set; `active` deactivates access
    while preserving the account and history (case 16); `shouldChangePassword`
    forces the temporary-password change on the first access.
    """

    id: str
    username: str
    name: str
    area: str
    contact: str
    roles: tuple[str, ...] = field(default_factory=tuple)
    active: bool = True
    passwordHash: str = ""
    shouldChangePassword: bool = False
    createdAt: str = ""

    def __post_init__(self) -> None:
        if not self.id or not self.username or not self.username.strip():
            raise DomainError("USER_INVALID", "El usuario requiere identificador y nombre de usuario.",
                              status_code=400)
        for role in self.roles:
            if role not in KNOWN_ROLES:
                raise UnknownRole(role)
        if not self.createdAt:
            self.createdAt = datetime.now().isoformat()

    @property
    def is_admin(self) -> bool:
        return ROLE_ADMIN in self.roles

    def to_payload(self) -> dict:
        """Public payload (camelCase, without the password hash)."""
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "area": self.area,
            "contact": self.contact,
            "roles": list(self.roles),
            "active": self.active,
            "shouldChangePassword": self.shouldChangePassword,
            "createdAt": self.createdAt,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "Usuario":
        return cls(
            id=payload["id"],
            username=payload["username"],
            name=payload.get("name", ""),
            area=payload.get("area", ""),
            contact=payload.get("contact", ""),
            roles=tuple(payload.get("roles", [])),
            active=payload.get("active", True),
            passwordHash=payload.get("passwordHash", ""),
            shouldChangePassword=payload.get("shouldChangePassword", False),
            createdAt=payload.get("createdAt", ""),
        )


def is_last_active_admin(users: list[Usuario], target_id: str) -> bool:
    """True when `target` is the only active administrator of `users`."""
    target = next((user for user in users if user.id == target_id), None)
    if target is None or not (target.active and target.is_admin):
        return False
    others = [user for user in users if user.id != target_id and user.active and user.is_admin]
    return not others
