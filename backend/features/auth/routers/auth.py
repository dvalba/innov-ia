"""Auth feature router (T-013, RF-1, RF-17).

Endpoints:
  POST /auth/login           -> 200 with token + user (401 on invalid credentials)
  POST /auth/logout          -> 200 (revokes the session)
  GET  /auth/me              -> 200 with the user's data and roles
  POST /auth/change-password -> 200 (409 when the change is not forced, 401 on
                                an invalid current password / no session)
"""

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.deps import AssistantCheckDep, SessionDep, TokenStoreDep, UserDirectoryDep
from features.auth.use_cases.change_password import ChangePasswordCommand, change_password
from features.auth.use_cases.login import LoginCommand, login
from features.auth.use_cases.logout import logout
from features.auth.use_cases.me import me
from shared.contracts.roles import ROLE_PROPOSER

auth_router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str


@auth_router.post("/login")
def login_endpoint(payload: LoginRequest, directory: UserDirectoryDep, tokens: TokenStoreDep,
                   background: BackgroundTasks, check: AssistantCheckDep) -> dict:
    result = login(LoginCommand(username=payload.username, password=payload.password, now=datetime.now()),
                   directory, tokens)
    # On-demand refinement verification on login (RF-11 decision #4): the
    # check runs in the background so the response is never blocked.
    if ROLE_PROPOSER in result.user.get("roles", ()):
        background.add_task(check)
    return {
        "token": result.session.token,
        "user": result.user,
        "mustChangePassword": result.must_change_password,
    }


@auth_router.post("/logout")
def logout_endpoint(session: SessionDep, tokens: TokenStoreDep) -> dict:
    logout(session.token, tokens)
    return {"ok": True}


@auth_router.get("/me")
def me_endpoint(session: SessionDep, directory: UserDirectoryDep) -> dict:
    return me(session, directory)


@auth_router.post("/change-password")
def change_password_endpoint(payload: ChangePasswordRequest, session: SessionDep,
                             directory: UserDirectoryDep) -> dict:
    updated = change_password(
        ChangePasswordCommand(user_id=session.user_id, current=payload.currentPassword,
                              new=payload.newPassword),
        session, directory,
    )
    return updated
