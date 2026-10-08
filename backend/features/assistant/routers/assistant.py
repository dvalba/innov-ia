"""Assistant router (T-062, RF-11, plan §3.1).

Endpoint (plan §3.1):
  POST  /assistant/check  -> 200 the verification summary (the assistant
                              availability is checked and the queue is
                              processed on demand: the number of refined
                              ideas and the failures)

Guarded to an active `proponente` session (401 without session, 403 for
other roles). A direct call runs the verification inline, so the response
reflects the real pass; the internal on-demand triggers (login, capture
start, improvement request — plan §4.5) execute the same check in the
background without blocking their main response (RF-11).
"""

from fastapi import APIRouter

from app.deps import AssistantCheckDep, role_dependency

assistant_router = APIRouter(prefix="/assistant", tags=["assistant"])

ProponentDep = role_dependency("proponente")


@assistant_router.post("/check")
def check_endpoint(session: ProponentDep, check: AssistantCheckDep) -> dict:
    """Verifies the assistant and processes the queue on demand (RF-11).

    Returns the pass summary `{"status", "refined", "failed", "pending"}`;
    `status` is `UNAVAILABLE` when the assistant is down (case 5: the ideas
    keep operating and the whole queue is processed at the next trigger,
    without expiration).
    """
    return check()
