"""
JWT Bearer Authentication and Role-Based Authorization for FastAPI.
Uses standard-library HMAC-SHA256 signed JWTs with server-side role verification.
"""
import base64
import hashlib
import hmac
import json
import os
import time
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Authentication"])
security_scheme = HTTPBearer(auto_error=False)

VALID_ROLES = {"EMPLOYEE", "MANAGER", "HR_PARTNER", "SYSTEM_ADMIN", "COMP_COMMITTEE"}


def _get_secret_key() -> bytes:
    secret = os.getenv("JWT_SECRET_KEY", "local-dev-jwt-secret-change-me")
    return secret.encode("utf-8")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(subject: str, role: str, expires_in: int = 3600) -> str:
    """Generates an HS256-signed JWT containing subject (`sub`), `role`, `iat`, and `exp`."""
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role '{role}'. Must be one of {sorted(VALID_ROLES)}.")
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": subject, "role": role, "iat": now, "exp": now + expires_in}
    signing_input = (
        f"{_b64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))}."
        f"{_b64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))}"
    )
    sig = hmac.new(_get_secret_key(), signing_input.encode("utf-8"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url_encode(sig)}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """Verifies HS256 signature and expiration; raises HTTP 401 if invalid."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Malformed token")
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(_get_secret_key(), signing_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("Invalid signature")
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("Token expired")
        if payload.get("role") not in VALID_ROLES or not payload.get("sub"):
            raise ValueError("Invalid claims")
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Dict[str, Any]:
    """FastAPI dependency requiring a valid Bearer JWT."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_access_token(credentials.credentials)


def require_roles(*allowed_roles: str):
    """FastAPI dependency enforcing server-verified role membership."""
    allowed_set = set(allowed_roles)

    def _checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if user.get("role") not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.get('role')}' is not authorized for this operation.",
            )
        return user

    return _checker


class TokenRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    subject: str
    role: str


def _load_configured_users() -> Dict[str, Dict[str, str]]:
    """
    Loads configured users from AUTH_USERS_JSON env var if provided,
    or falls back to local development test accounts using DEV_AUTH_PASSWORD env var.
    """
    raw = os.getenv("AUTH_USERS_JSON", "").strip()
    if raw:
        return json.loads(raw)
    dev_pw = os.getenv("DEV_AUTH_PASSWORD", "")
    if not dev_pw:
        return {}
    return {
        "hr.partner@company.org": {"password": dev_pw, "role": "HR_PARTNER"},
        "manager.lead@company.org": {"password": dev_pw, "role": "MANAGER"},
        "sys.admin@company.org": {"password": dev_pw, "role": "SYSTEM_ADMIN"},
        "employee.user@company.org": {"password": dev_pw, "role": "EMPLOYEE"},
    }


@router.post("/token", response_model=TokenResponse)
def issue_access_token(req: TokenRequest):
    """Issues a signed JWT after verifying credentials against configured users."""
    users = _load_configured_users()
    user_rec = users.get(req.email.strip().lower())
    if not user_rec or not hmac.compare_digest(user_rec.get("password", ""), req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    role = user_rec["role"]
    token = create_access_token(subject=req.email.strip().lower(), role=role)
    return TokenResponse(access_token=token, subject=req.email.strip().lower(), role=role)
