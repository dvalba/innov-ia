"""Organization feature domain: the company context document (RF-21, D13).

The company context is the **single editable document** the administrator
manages. It is the knowledge source behind every AI operation on the platform
(RF-22). It has two parts:

- `profile`: the fixed section of the template (name, sector, description,
  mission, strategic objectives). The v2.0 organization profile now *lives
  inside* this document (D7 replacement, D13).
- `guideText`: free text (strategic alignment, priorities, innovation lines,
  vocabulary and reference information) that the AI injects in all its
  operations.

The document also round-trips to a plain-text template (RF-21): `render_template`
produces the downloadable skeleton and `parse_template` reads a filled file back
into the `{profile, guideText}` structure so an upload replaces the whole
document (case 25). Pure domain: no FastAPI/Pydantic.
"""

from dataclasses import dataclass, field

PROFILE_KEYS: tuple[str, ...] = ("name", "sector", "description", "mission")

EMPTY_PROFILE: dict = {
    "name": "",
    "sector": "",
    "description": "",
    "mission": "",
    "strategicObjectives": [],
}


def clean_profile(data: dict) -> dict:
    """Normalizes a raw profile mapping into the canonical profile shape.

    Strips blanks and de-duplicates the strategic objectives (duplicates and
    blank entries are dropped) so every stored/loaded document has the
    documented shape.
    """
    data = data or {}
    seen: set[str] = set()
    objectives: list[str] = []
    for raw in data.get("strategicObjectives", []) or []:
        target = str(raw).strip()
        if target and target not in seen:
            seen.add(target)
            objectives.append(target)
    return {
        "name": str(data.get("name", "")).strip(),
        "sector": str(data.get("sector", "")).strip(),
        "description": str(data.get("description", "")).strip(),
        "mission": str(data.get("mission", "")).strip(),
        "strategicObjectives": objectives,
    }


def _profile_blank(profile: dict) -> bool:
    if any(str(profile.get(key, "")).strip() for key in PROFILE_KEYS):
        return False
    return not list(profile.get("strategicObjectives") or [])


@dataclass
class CompanyContext:
    """The single company-context document (RF-21).

    `profile` holds the fixed template section; `guideText` the free guidance
    text; `updatedAt` the ISO-8601 timestamp of the last write (empty for a
    never-set context).
    """

    profile: dict = field(default_factory=lambda: {
        **EMPTY_PROFILE, "strategicObjectives": []
    })
    guideText: str = ""
    updatedAt: str = ""

    @property
    def is_empty(self) -> bool:
        """True when there is no usable content (case 24, RNF-12): a blank
        profile AND a blank guide text."""
        return _profile_blank(self.profile) and not str(self.guideText).strip()

    @classmethod
    def empty(cls) -> "CompanyContext":
        """The blank context, used when the administrator has not defined one."""
        return cls(profile={**EMPTY_PROFILE, "strategicObjectives": []},
                   guideText="", updatedAt="")

    def to_payload(self) -> dict:
        """The stored camelCase document payload (plan §2.8)."""
        return {
            "profile": {**self.profile, "strategicObjectives": list(
                self.profile.get("strategicObjectives") or [])},
            "guideText": self.guideText,
            "updatedAt": self.updatedAt,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "CompanyContext":
        """Rebuilds a document from a stored payload, tolerating missing keys."""
        payload = payload or {}
        return cls(
            profile=clean_profile(payload.get("profile")),
            guideText=str(payload.get("guideText", "")).strip(),
            updatedAt=str(payload.get("updatedAt", "")),
        )


# ---------------------------------------------------------------------------
# Plain-text template (RF-21): render a document and parse a file back.
# A filled file round-trips through the two helpers; a file missing the
# section markers is "corrupt" (case 25).
# ---------------------------------------------------------------------------

def render_template(context: CompanyContext, template: bool = False) -> str:
    """Renders the company context as the `text/plain` document.

    With `template=True` the fixed section is blanked (placeholders) so the
    result is the downloadable skeleton; otherwise it reflects `context`.
    """
    profile = {**EMPTY_PROFILE, "strategicObjectives": []} if template else dict(
        context.profile)
    lines = ["# Contexto de empresa — Innov-IA", "[PERFIL]"]
    for key in PROFILE_KEYS:
        lines.append(f"{key}: {profile.get(key, '')}".rstrip())
    lines.append("strategicObjectives:")
    for objective in profile.get("strategicObjectives") or []:
        lines.append(f"- {objective}")
    if template:
        lines.append("- ")
    lines.append(
        "# Alineación estratégica (objetivos, prioridades, líneas de innovación)"
    )
    lines.append("# y vocabulario e información de referencia para la IA.")
    lines.append("[GUÍA]")
    if not template:
        lines.append(context.guideText)
    lines.append("[/GUÍA]")
    return "\n".join(lines)


def parse_template(text: str) -> dict:
    """Parses a text document back into `{"profile": {...}, "guideText": str}`.

    Raises `ValueError` when the mandatory section markers are missing (the
    file is corrupt, case 25). Within `[PERFIL]` only the known `key: value`
    lines and the `- ` bullets are captured; section labels are ignored so the
    template round-trips cleanly.
    """
    if "[PERFIL]" not in text or "[GUÍA]" not in text:
        raise ValueError(
            "El archivo no contiene las secciones [PERFIL] y [GUÍA] del contexto."
        )
    perfil_start = text.index("[PERFIL]") + len("[PERFIL]")
    guia_start = text.index("[GUÍA]")
    perfil_block = text[perfil_start:guia_start]

    guia_body = text[guia_start + len("[GUÍA]"):]
    end_marker = "[/GUÍA]"
    if end_marker in guia_body:
        guia_body = guia_body[: guia_body.index(end_marker)]

    profile: dict = {key: "" for key in PROFILE_KEYS}
    profile["strategicObjectives"] = []
    reading_objectives = False
    for line in perfil_block.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "strategicObjectives:":
            reading_objectives = True
            continue
        if stripped.startswith("-"):
            if reading_objectives:
                item = stripped[1:].strip()
                if item:
                    profile["strategicObjectives"].append(item)
            continue
        if ":" in stripped:
            key = stripped.split(":", 1)[0].strip().lower()
            if key in PROFILE_KEYS:
                profile[key] = stripped.split(":", 1)[1].strip()

    return {"profile": profile, "guideText": guia_body.strip()}
