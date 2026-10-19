"""Upload company context use case (RF-21, D14, case 25).

Receives the contents of a text file (sent as a JSON `content` field, no
multipart — D14) and **replaces** the current company-context document in its
entirety (RF-21). The text must parse back into the template structure
(`[PERFIL]` + `[GUÍA]`, case 25): a blank file or a file whose sections are
missing is "corrupt" and the current context is left untouched.

The guide section may stay empty (only the profile filled); the profile is
still required and blanked only when it has no useful content, in which case
upload fails.
"""

from datetime import datetime

from features.org.domain.company_context import CompanyContext, clean_profile, parse_template
from features.org.infrastructure.org_store import OrgStore
from shared.exceptions.handlers import DomainError


def upload_context(store: OrgStore, text: str) -> dict:
    """Parses the uploaded file and replaces the current document (400 on
    blank / corrupt content, case 25)."""
    if text is None or not str(text).strip():
        raise DomainError(
            "CONTEXT_UPLOAD_EMPTY",
            "El archivo de contexto está vacío.",
            status_code=400,
        )
    try:
        parsed = parse_template(str(text))
    except ValueError as exc:
        raise DomainError(
            "CONTEXT_UPLOAD_INVALID",
            str(exc),
            status_code=400,
        ) from exc

    profile = clean_profile(parsed.get("profile"))
    if not (profile["name"] or profile["sector"] or profile["description"]
            or profile["mission"] or profile["strategicObjectives"]):
        raise DomainError(
            "CONTEXT_UPLOAD_INVALID",
            "El perfil de la organización en el archivo está vacío.",
            status_code=400,
        )

    document = CompanyContext(
        profile=profile,
        guideText=str(parsed.get("guideText", "")).strip(),
        updatedAt=datetime.now().isoformat(),
    )
    return store.put(document.to_payload())
