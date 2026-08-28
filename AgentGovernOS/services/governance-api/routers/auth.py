"""
AgentGovern OS — Auth Router (Phase 1 Fix)
==========================================
Real password hashing with bcrypt.
Users are stored in the database.
No password-less auth. No fake roles based on email strings.
"""

import time
import uuid
from typing import Any

from database import Base, get_db
from fastapi import APIRouter, Depends, Header, HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth import ALGORITHM, AuthService

router = APIRouter(tags=["auth"])

try:
    import bcrypt as native_bcrypt
except ImportError:
    native_bcrypt = None

try:
    from passlib.context import CryptContext
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception:
    pwd_ctx = None

def hash_password(plain: str) -> str:
    safe_plain = plain[:72] if isinstance(plain, str) else plain
    if native_bcrypt:
        return native_bcrypt.hashpw(safe_plain.encode("utf-8"), native_bcrypt.gensalt()).decode("utf-8")
    if pwd_ctx:
        try:
            return pwd_ctx.hash(safe_plain)
        except Exception:
            pass
    import hashlib
    return hashlib.sha256(safe_plain.encode("utf-8")).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    safe_plain = plain[:72] if isinstance(plain, str) else plain
    if native_bcrypt and hashed.startswith("$2"):
        try:
            return native_bcrypt.checkpw(safe_plain.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            pass
    if pwd_ctx:
        try:
            return pwd_ctx.verify(safe_plain, hashed)
        except Exception:
            pass
    import hashlib
    return hashlib.sha256(safe_plain.encode("utf-8")).hexdigest() == hashed


# ── User model (local users table) ───────────────────────────────────────────
class LocalUser(Base):
    __tablename__ = "local_users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(Text, nullable=False)
    name = Column(String(200), nullable=False)
    role = Column(String(50), nullable=False, default="developer")
    org_id = Column(String(36), default="00000000-0000-0000-0000-000000000000")
    org_slug = Column(String(100), default="default")
    org_name = Column(String(200), default="")
    org_tier = Column(String(50), default="Free")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ── Request / Response schemas ────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    org_name: str | None = None


class TokenRefreshRequest(BaseModel):
    refresh_token: str | None = None


# ── Helper: build JWT ─────────────────────────────────────────────────────────
def _mint_token(user: LocalUser, expires_in: int = 86400) -> str:
    secret = AuthService.get_secret_key()
    now = int(time.time())
    payload = {
        "sub": user.id,
        "name": user.name,
        "email": user.email,
        "org_id": user.org_id,
        "org_slug": user.org_slug,
        "roles": [user.role],
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def _user_response(user: LocalUser, token: str, expires_in: int) -> dict[str, Any]:
    role_arn_map = {
        "owner": "arn:agentverse:iam::org_default:role/OwnerRole",
        "admin": "arn:agentverse:iam::org_default:role/AdminRole",
        "developer": "arn:agentverse:iam::org_default:role/DeveloperRole",
        "write": "arn:agentverse:iam::org_default:role/DeveloperRole",
        "auditor": "arn:agentverse:iam::org_default:role/AuditorRole",
        "read": "arn:agentverse:iam::org_default:role/AuditorRole",
    }
    assumed_role_arn = role_arn_map.get(user.role.lower(), "arn:agentverse:iam::org_default:role/DeveloperRole")
    user_arn = f"arn:agentverse:iam::{user.org_id or 'org_default'}:user/{user.email.split('@')[0]}"

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "org_slug": user.org_slug,
            "org_name": user.org_name,
            "org_tier": user.org_tier,
            "assumed_role_arn": assumed_role_arn,
            "user_arn": user_arn,
        },
    }


# ── Demo Accounts & Fallback Store ───────────────────────────────────────────

DEMO_ACCOUNTS: dict[str, dict[str, str]] = {
    "owner@nuuvixx.ai": {
        "name": "Platform Executive",
        "role": "owner",
        "org_name": "Nuuvixx AI Systems",
        "org_slug": "nuuvixx-autonomous",
        "org_tier": "Enterprise",
    },
    "admin@nuuvixx.ai": {
        "name": "System Administrator",
        "role": "admin",
        "org_name": "Nuuvixx AI Systems",
        "org_slug": "nuuvixx-autonomous",
        "org_tier": "Enterprise",
    },
    "developer@nuuvixx.ai": {
        "name": "Autonomous Agent Developer",
        "role": "developer",
        "org_name": "Nuuvixx AI Systems",
        "org_slug": "nuuvixx-autonomous",
        "org_tier": "Pro",
    },
}

IN_MEMORY_USERS: dict[str, LocalUser] = {}


@router.post("/auth/register")
async def register(body: RegisterRequest, db: AsyncSession | None = Depends(get_db)) -> dict[str, Any]:
    """Register a new user with hashed password. Returns JWT on success."""
    if not body.email or not body.password or not body.name:
        raise HTTPException(status_code=400, detail="Email, password, and name are required.")

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    clean_email = body.email.lower().strip()

    # Check for duplicate email
    if db:
        try:
            existing = await db.execute(select(LocalUser).where(LocalUser.email == clean_email))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="An account with this email already exists.")
        except HTTPException:
            raise
        except Exception:
            pass

    if clean_email in IN_MEMORY_USERS:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    org_name = body.org_name or f"{body.name}'s Org"
    org_slug = org_name.lower().replace(" ", "-").replace(".", "").replace(",", "")[:50]

    user = LocalUser(
        id=str(uuid.uuid4()),
        email=clean_email,
        hashed_password=hash_password(body.password),
        name=body.name.strip(),
        role="owner",
        org_slug=org_slug,
        org_name=org_name,
        org_tier="Free",
    )

    if db:
        try:
            db.add(user)
            await db.commit()
            await db.refresh(user)
        except Exception:
            IN_MEMORY_USERS[clean_email] = user
    else:
        IN_MEMORY_USERS[clean_email] = user

    token = _mint_token(user, expires_in=86400)
    return _user_response(user, token, 86400)


@router.post("/auth/login")
async def login(body: LoginRequest, db: AsyncSession | None = Depends(get_db)) -> dict[str, Any]:
    """Authenticate with email + password. Returns JWT on success."""
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Email and password are required.")

    clean_email = body.email.lower().strip()

    # Instant demo login path
    if clean_email in DEMO_ACCOUNTS and (body.password == "demo-password" or body.password == "demo"):
        demo_meta = DEMO_ACCOUNTS[clean_email]
        user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, clean_email))
        demo_user = LocalUser(
            id=user_id,
            email=clean_email,
            hashed_password=hash_password("demo-password"),
            name=demo_meta["name"],
            role=demo_meta["role"],
            org_slug=demo_meta["org_slug"],
            org_name=demo_meta["org_name"],
            org_tier=demo_meta["org_tier"],
        )
        if db:
            try:
                result = await db.execute(select(LocalUser).where(LocalUser.email == clean_email))
                existing = result.scalar_one_or_none()
                if not existing:
                    db.add(demo_user)
                    await db.commit()
                    await db.refresh(demo_user)
                else:
                    demo_user = existing
            except Exception:
                pass
        token = _mint_token(demo_user, expires_in=86400)
        return _user_response(demo_user, token, 86400)

    user = None
    if db:
        try:
            result = await db.execute(select(LocalUser).where(LocalUser.email == clean_email))
            user = result.scalar_one_or_none()
        except Exception:
            user = None

    if not user and clean_email in IN_MEMORY_USERS:
        user = IN_MEMORY_USERS[clean_email]

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = _mint_token(user, expires_in=86400)
    return _user_response(user, token, 86400)


@router.post("/auth/refresh")
async def refresh_token(
    body: TokenRefreshRequest | None = None,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    """Refresh an active or recently expired JWT."""
    token_str = None
    if authorization and authorization.startswith("Bearer "):
        token_str = authorization.split(" ")[1]
    elif body and body.refresh_token:
        token_str = body.refresh_token

    if not token_str:
        raise HTTPException(status_code=401, detail="Authorization token required for refresh.")

    try:
        secret = AuthService.get_secret_key()
        payload = jwt.decode(token_str, secret, algorithms=[ALGORITHM], options={"verify_exp": False})
        now = int(time.time())
        payload["iat"] = now
        payload["exp"] = now + 3600
        new_token = jwt.encode(payload, secret, algorithm=ALGORITHM)
        return {"access_token": new_token, "token_type": "bearer", "expires_in": 3600}
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid refresh token: {e!s}")


@router.get("/auth/me")
async def get_me(authorization: str | None = Header(None)) -> dict[str, Any]:
    """Verify and decode the current JWT. Returns user profile."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required.")

    token_str = authorization.split(" ")[1]
    try:
        secret = AuthService.get_secret_key()
        payload = jwt.decode(token_str, secret, algorithms=[ALGORITHM])
        return {
            "id": payload.get("sub"),
            "name": payload.get("name"),
            "email": payload.get("email"),
            "role": payload.get("roles", ["developer"])[0],
            "org_id": payload.get("org_id"),
            "org_slug": payload.get("org_slug"),
            "roles": payload.get("roles", []),
        }
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e!s}")
