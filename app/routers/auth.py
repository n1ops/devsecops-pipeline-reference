import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import update
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.auth import (
    create_access_token,
    hash_password,
    oauth2_scheme,
    revoke_token,
    verify_password,
)
from app.database import get_db
from app.models import User
from app.rate_limit import limiter
from app.schemas import (
    PasswordChange,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
# Dummy hash for timing equalization on non-existent user lookups
_DUMMY_HASH = "$2b$12$LJ3m4ys3Lg2HEOiLcoMxsez0FXOH0idstXJiGfOBfWxJCFb.FhIm6"


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == user_in.username).first()
    if existing:
        # Perform dummy hash to equalize timing with successful registration
        hash_password("dummy-password-for-timing")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Registration failed",
        )
    user = User(
        username=user_in.username,
        hashed_password=hash_password(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("User registered: %s", user.username)
    return user


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_in.username).first()

    if not user:
        # Perform dummy hash check to equalize response timing with real users
        verify_password(user_in.password, _DUMMY_HASH)
        logger.warning("Login attempt for non-existent user: %s", user_in.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Check account lockout (SQLite returns naive datetimes, so compare as naive UTC)
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    if user.locked_until and user.locked_until > now_utc:
        logger.warning("Login attempt on locked account: %s", user.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not verify_password(user_in.password, user.hashed_password):
        # Atomic increment to avoid race condition
        new_count = user.failed_login_attempts + 1
        update_values = {"failed_login_attempts": User.failed_login_attempts + 1}
        if new_count >= MAX_FAILED_ATTEMPTS:
            update_values["locked_until"] = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=LOCKOUT_MINUTES)
            logger.warning("Account locked after %d failed attempts: %s", new_count, user.username)
        db.execute(
            update(User).where(User.id == user.id).values(**update_values)
        )
        db.commit()
        logger.warning("Failed login for user: %s (attempt %d)", user.username, new_count)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Reset lockout on successful login (atomic update)
    db.execute(
        update(User).where(User.id == user.id).values(
            failed_login_attempts=0,
            locked_until=None,
        )
    )
    db.commit()

    access_token = create_access_token(data={"sub": user.username})
    logger.info("User logged in: %s", user.username)
    return {"access_token": access_token}


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    revoke_token(token, db)
    logger.info("Token revoked via logout for user: %s", current_user.username)
    return {"detail": "Successfully logged out"}


@router.post("/change-password", status_code=status.HTTP_200_OK)
@limiter.limit("3/minute")
def change_password(
    request: Request,
    passwords: PasswordChange,
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    if not verify_password(passwords.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )
    if verify_password(passwords.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )
    current_user.hashed_password = hash_password(passwords.new_password)
    current_user.password_changed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    revoke_token(token, db)
    db.commit()
    logger.info("Password changed for user: %s", current_user.username)
    return {"detail": "Password changed successfully"}


@router.post("/refresh", response_model=Token)
@limiter.limit("5/minute")
def refresh_token(
    request: Request,
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    revoke_token(token, db)
    new_token = create_access_token(data={"sub": current_user.username})
    logger.info("Token refreshed for user: %s", current_user.username)
    return {"access_token": new_token}
