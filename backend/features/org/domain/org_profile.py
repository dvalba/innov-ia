"""Organization feature domain: the organization profile (decision D7 replacement).

The organization profile is the knowledge source behind the per-turn quick
options the assistant offers while capturing an idea. It is admin-managed
through the dedicated panel and read (never written) by the capture flow.
Pure domain: no FastAPI/Pydantic.
"""

from dataclasses import dataclass, field


@dataclass
class OrgProfile:
    """The organization profile captured and managed by the administrator.

    `strategicObjectives` is a list of short statements the assistant uses to
    ground its alignment options; it may be empty when the organization has
    not defined any yet.
    """

    name: str
    sector: str
    description: str
    mission: str
    strategicObjectives: list[str] = field(default_factory=list)

    def to_payload(self) -> dict:
        """Stored camelCase payload (identical to the public one)."""
        return {
            "name": self.name,
            "sector": self.sector,
            "description": self.description,
            "mission": self.mission,
            "strategicObjectives": list(self.strategicObjectives),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "OrgProfile":
        objectives = payload.get("strategicObjectives", [])
        return cls(
            name=payload.get("name", ""),
            sector=payload.get("sector", ""),
            description=payload.get("description", ""),
            mission=payload.get("mission", ""),
            strategicObjectives=[str(obj) for obj in objectives],
        )
