"""Authentication system for Cogent - JWT-based auth with user management.

This replaces the simple credential store with a proper authentication system
supporting user registration, login, JWT tokens, and workspace isolation.
"""

from __future__ import annotations

import hashlib
import secrets
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

from pydantic import BaseModel, EmailStr, Field
from jose import jwt, JWTError
from passlib.context import CryptContext

from cogent_constants import MEMORY_DIR, ensure_dirs
from cogent_config import get_config

logger = logging.getLogger("cogent.auth_v2")

# ─── Password hashing ───
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ─── JWT Configuration ───
_cfg = get_config()
SECRET_KEY = _cfg.auth_secret_key or "dev-secret-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
REFRESH_TOKEN_EXPIRE_DAYS = 30

# ─── Models ───


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    created_at: datetime
    workspace_id: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    user_id: Optional[str] = None
    exp: Optional[int] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ─── Storage ───

_users_cache: Dict[str, Dict[str, Any]] = {}
_cache_loaded = False


def _users_path() -> Path:
    return MEMORY_DIR / "users.json"


def _load_users() -> Dict[str, Dict[str, Any]]:
    global _users_cache, _cache_loaded
    if _cache_loaded:
        return _users_cache

    path = _users_path()
    if not path.is_file():
        _users_cache = {}
        _cache_loaded = True
        return _users_cache

    try:
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        _users_cache = data.get("users", {})
    except Exception as e:
        logger.warning("Failed to load users: %s", e)
        _users_cache = {}
    _cache_loaded = True
    return _users_cache


def _save_users(users: Dict[str, Dict[str, Any]]) -> None:
    global _users_cache
    _users_cache = users
    path = _users_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    import json
    path.write_text(json.dumps({"users": users}, indent=2, default=str), encoding="utf-8")


# ─── Core Functions ───


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        exp = payload.get("exp")
        token_type = payload.get("type")
        if user_id is None or token_type != "access":
            return None
        return TokenData(user_id=user_id, exp=exp)
    except JWTError:
        return None


def decode_refresh_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        exp = payload.get("exp")
        token_type = payload.get("type")
        if user_id is None or token_type != "refresh":
            return None
        return TokenData(user_id=user_id, exp=exp)
    except JWTError:
        return None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    users = _load_users()
    return users.get(user_id)


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    users = _load_users()
    for user in users.values():
        if user.get("email", "").lower() == email.lower():
            return user
    return None


def create_user(email: str, password: str, name: Optional[str] = None) -> Dict[str, Any]:
    """Create a new user with their own workspace."""
    users = _load_users()
    
    # Check if email exists
    if get_user_by_email(email):
        raise ValueError("Email already registered")
    
    user_id = secrets.token_urlsafe(16)
    workspace_id = f"ws_{secrets.token_urlsafe(12)}"
    hashed_pw = hash_password(password)
    now = datetime.utcnow()
    
    user = {
        "id": user_id,
        "email": email.lower(),
        "name": name,
        "password_hash": hashed_pw,
        "workspace_id": workspace_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "is_active": True,
    }
    
    users[user_id] = user
    _save_users(users)
    logger.info("Created user: %s (%s)", email, user_id)
    return user


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    user = get_user_by_email(email)
    if not user:
        return None
    if not user.get("is_active", True):
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def update_user(user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    users = _load_users()
    if user_id not in users:
        return None
    users[user_id].update(updates)
    users[user_id]["updated_at"] = datetime.utcnow().isoformat()
    _save_users(users)
    return users[user_id]


def create_tokens(user: Dict[str, Any]) -> Token:
    access_token = create_access_token({"sub": user["id"], "workspace_id": user["workspace_id"]})
    refresh_token = create_refresh_token({"sub": user["id"]})
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user.get("name"),
            created_at=datetime.fromisoformat(user["created_at"]),
            workspace_id=user["workspace_id"],
        ),
    )


def refresh_access_token(refresh_token: str) -> Optional[str]:
    token_data = decode_refresh_token(refresh_token)
    if not token_data:
        return None
    user = get_user_by_id(token_data.user_id)
    if not user or not user.get("is_active", True):
        return None
    return create_access_token({"sub": user["id"], "workspace_id": user["workspace_id"]})


# ─── Dependency for FastAPI ───

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """Dependency to get current authenticated user."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_data = decode_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_user_by_id(token_data.user_id)
    if not user or not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[Dict[str, Any]]:
    """Optional authentication - returns user if valid token, None otherwise."""
    if not credentials:
        return None
    token_data = decode_token(credentials.credentials)
    if not token_data:
        return None
    user = get_user_by_id(token_data.user_id)
    if not user or not user.get("is_active", True):
        return None
    return user


# ─── Workspace utilities ───

def get_user_workspace(user: Dict[str, Any]) -> str:
    """Get the workspace ID for a user."""
    return user.get("workspace_id", f"ws_{user['id'][:12]}")


def ensure_user_workspace(user: Dict[str, Any]) -> str:
    """Ensure user has a workspace, create if missing."""
    workspace_id = user.get("workspace_id")
    if not workspace_id:
        workspace_id = f"ws_{secrets.token_urlsafe(12)}"
        update_user(user["id"], {"workspace_id": workspace_id})
    return workspace_id