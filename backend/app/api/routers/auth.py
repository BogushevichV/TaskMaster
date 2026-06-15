import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from backend.app.crud.user import create_user, get_user_by_email, get_user_by_username
from backend.app.models.user import User
from backend.app.schemas.user import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenPair,
    TokenRefresh,
    UserCreate,
    UserRead,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory store for password reset tokens (replace with Redis in production)
_reset_tokens: dict[str, tuple[str, datetime]] = {}


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    if await get_user_by_username(db, data.username):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username already taken")
    if await get_user_by_email(db, data.email):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")
    return await create_user(db, data)


@router.post("/login", response_model=TokenPair)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    user = await get_user_by_username(db, form.username)
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is inactive")
    return TokenPair(
        access_token=create_access_token(user.id, {"role": user.role.value}),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/login/json", response_model=TokenPair)
async def login_json(data: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    user = await get_user_by_username(db, data.username)
    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is inactive")
    return TokenPair(
        access_token=create_access_token(user.id, {"role": user.role.value}),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(data: TokenRefresh, db: AsyncSession = Depends(get_db)) -> TokenPair:
    payload = verify_token(data.refresh_token, "refresh")
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    from app.crud.user import get_user_by_id

    user = await get_user_by_id(db, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return TokenPair(
        access_token=create_access_token(user.id, {"role": user.role.value}),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/password-reset/request")
async def password_reset_request(
    data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    user = await get_user_by_email(db, data.email)
    if user is None:
        return {"message": "If the email exists, a reset link was sent"}
    token = secrets.token_urlsafe(32)
    _reset_tokens[token] = (user.email, datetime.now(timezone.utc) + timedelta(hours=1))
    # TODO: send email via SMTP when configured
    return {"message": "If the email exists, a reset link was sent", "dev_token": token}


@router.post("/password-reset/confirm")
async def password_reset_confirm(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    entry = _reset_tokens.get(data.token)
    if entry is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired token")
    email, expires = entry
    if datetime.now(timezone.utc) > expires:
        _reset_tokens.pop(data.token, None)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token expired")
    user = await get_user_by_email(db, email)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.hashed_password = hash_password(data.new_password)
    _reset_tokens.pop(data.token, None)
    return {"message": "Password updated successfully"}
