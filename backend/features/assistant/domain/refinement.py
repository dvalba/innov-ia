"""Refinement rules for manual ideas (T-060, plan §4.5, spec RF-11).

Pure domain module (Constitution §4.2). It owns two things:
  1. The queue selection: ideas in `EN_DESARROLLO` with origin `manual` that
     still have no valid refined version, ordered from the oldest to the most
     recent (RF-11).
  2. The interpretation of the assistant's raw reply: the 7 fields are
     validated and any uninterpretable reply is a failure (spec case 6/14).
"""

import json
from collections.abc import Callable, Iterable
from typing import Any

from shared.contracts.idea_ledger import IDEA_FIELDS, ORIGIN_MANUAL, STATE_EN_DESARROLLO

# Requested-by marker that identifies a refinement pass (plan §2.5).
REQUESTED_BY_REFINEMENT = "refinement"

# A version in one of these statuses means the idea has already been refined
# for the current request, so it is out of the queue (RF-11 "válida").
_REFINED_STATUSES = ("PENDIENTE", "ACEPTADA", "VIGENTE")

# Sub-fields that the structured objects must contain (schema plan §2.2).
_PROPOSER_KEYS = ("name", "area", "contact")
_RESOURCE_KEYS = ("time", "people", "budget")


def needs_refinement(idea: dict, versions: Iterable[dict] = ()) -> bool:
    """`True` when the idea belongs to the refinement queue (RF-11).

    Criteria (conjunction): origin is `manual`, state is `EN_DESARROLLO`, and
    there is no refinement version in a refined status. A version whose only
    request was discarded does not count, so the idea may be refined again.
    """
    if idea.get("origin") != ORIGIN_MANUAL or idea.get("state") != STATE_EN_DESARROLLO:
        return False
    for version in versions:
        if (
            version.get("requestedBy") == REQUESTED_BY_REFINEMENT
            and version.get("status") in _REFINED_STATUSES
        ):
            return False
    return True


def build_refinement_queue(
    ideas: Iterable[dict], versions_for: Callable[[str], Iterable[dict]]
) -> list[dict]:
    """Orders the queue from the oldest to the most recent (RF-11).

    `versions_for` receives an idea id and yields its versions; it is injected
    by the caller so this module stays free of any store dependency.
    """
    candidates = [
        idea for idea in ideas if needs_refinement(idea, versions_for(idea.get("id", "")))
    ]
    candidates.sort(key=lambda idea: (idea.get("createdAt") or "", idea.get("id") or ""))
    return candidates


def _extract_json_object(raw: str) -> Any:
    """Locates and parses the first JSON object in `raw`.

    Assistant replies are often wrapped in code fences or surrounded by prose;
    the first `{` and the matching last `}` delimit the payload. Raises
    `ValueError` when no valid object can be extracted.
    """
    text = raw.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("sin objeto JSON")
    return json.loads(text[start : end + 1])


def _non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _non_empty_obj(value: Any, keys: tuple[str, ...]) -> bool:
    if not isinstance(value, dict):
        return False
    return all(_non_empty_str(value.get(key)) for key in keys)


def interpret_fields(raw: str) -> dict | None:
    """Validates the 7 fields in the assistant reply; `None` on failure (case 14).

    The reply must contain exactly the 7 idea fields (plan §2.2): the four
    scalar strings plus `title`, with `proponent` and `estimatedResources` as
    structured objects whose sub-fields are present and non-empty.
    """
    try:
        data = _extract_json_object(raw)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    for field in IDEA_FIELDS:
        if field not in data:
            return None
    if not _non_empty_str(data.get("title")):
        return None
    for field in ("description", "problem", "expectedBenefit", "strategicAlignment"):
        if not _non_empty_str(data.get(field)):
            return None
    if not _non_empty_obj(data.get("proponent"), _PROPOSER_KEYS):
        return None
    resources = data.get("estimatedResources")
    if not isinstance(resources, dict):
        return None
    if not all(isinstance(resources.get(key), str) for key in _RESOURCE_KEYS):
        return None
    return {field: data[field] for field in IDEA_FIELDS}
