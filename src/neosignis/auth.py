"""Local development bearer token or verified Cognito access token."""

import asyncio
import hmac
import os
from dataclasses import dataclass
from urllib.parse import urlparse

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import Depends


bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Settings:
    app_env: str
    auth_mode: str
    dev_api_token: str
    issuer: str
    client_id: str
    inference_url: str

    @classmethod
    def from_env(cls):
        return cls(
            os.getenv("APP_ENV", "local"), os.getenv("AUTH_MODE", "dev_token"),
            os.getenv("DEV_API_TOKEN", ""), os.getenv("COGNITO_ISSUER", ""),
            os.getenv("COGNITO_CLIENT_ID", ""), os.getenv("INFERENCE_URL", "http://127.0.0.1:8001"),
        )

    def validate(self):
        if self.app_env not in {"local", "cloud"}:
            raise ValueError("APP_ENV must be local or cloud")
        if self.auth_mode == "dev_token":
            if self.app_env != "local" or len(self.dev_api_token) < 32:
                raise ValueError("dev_token requires local mode and a random token of at least 32 characters")
        elif self.auth_mode == "cognito":
            host = urlparse(self.issuer)
            if host.scheme != "https" or not host.hostname or not host.hostname.startswith("cognito-idp.") or not host.hostname.endswith(".amazonaws.com") or not self.client_id:
                raise ValueError("Cognito requires a regional HTTPS issuer and client ID")
        else:
            raise ValueError("Unknown AUTH_MODE")
        url = urlparse(self.inference_url)
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}:
            raise ValueError("INFERENCE_URL must be a configured HTTP(S) service origin")


class Authenticator:
    def __init__(self, settings: Settings):
        settings.validate()
        self.settings = settings
        self.jwks = None
        if settings.auth_mode == "cognito":
            from jwt import PyJWKClient
            self.jwks = PyJWKClient(settings.issuer + "/.well-known/jwks.json", cache_keys=True, timeout=3)

    def verify(self, token: str) -> str:
        if self.settings.auth_mode == "dev_token":
            if hmac.compare_digest(token.encode(), self.settings.dev_api_token.encode()):
                return "local-developer"
            raise ValueError("Invalid token")
        import jwt
        key = self.jwks.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token, key.key, algorithms=["RS256"], issuer=self.settings.issuer,
            options={"verify_aud": False, "require": ["exp", "iat", "sub", "token_use", "client_id"]},
        )
        if claims["token_use"] != "access" or claims["client_id"] != self.settings.client_id or not claims["sub"]:
            raise ValueError("Wrong token purpose or client")
        return claims["sub"]

    async def dependency(self, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
        if credentials is None:
            raise HTTPException(401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
        try:
            return await asyncio.to_thread(self.verify, credentials.credentials)
        except Exception:
            # Includes key-fetch failure: fail closed without leaking token material.
            raise HTTPException(401, detail="Invalid or unverifiable access token", headers={"WWW-Authenticate": "Bearer"}) from None
