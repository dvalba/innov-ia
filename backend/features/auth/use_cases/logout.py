"""Logout use case (T-012, RF-1).

Revokes the session token, closing the access and returning to the login
screen on the client side (interceptor).
"""

from features.auth.infrastructure.token_store import TokenStore


def logout(token: str, tokens: TokenStore) -> None:
    """Revokes the token. Safe for unknown tokens."""
    tokens.revoke(token)
