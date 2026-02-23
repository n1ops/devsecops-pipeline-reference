import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import jwt
from jwt.exceptions import PyJWTError

from app.config import settings
from app.database import get_db
from app.models import User, TokenBlocklist

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    salt = _bcrypt.gensalt()
    return _bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    now = datetime.now(timezone.utc)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "iss": settings.APP_NAME,
        "aud": settings.APP_NAME,
        "jti": secrets.token_hex(16),
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=settings.APP_NAME,
            issuer=settings.APP_NAME,
        )
        username: str | None = payload.get("sub")
        jti: str | None = payload.get("jti")
        if username is None or jti is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception

    # Check token blocklist
    if db.query(TokenBlocklist).filter(TokenBlocklist.jti == jti).first():
        logger.warning("Blocked token used: jti=%s", jti)
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    # Reject tokens for locked accounts
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    if user.locked_until and user.locked_until > now_utc:
        logger.warning("Token used for locked account: %s", username)
        raise credentials_exception

    # Reject tokens issued before last password change
    if user.password_changed_at:
        iat = payload.get("iat")
        if iat:
            token_issued = datetime.fromtimestamp(iat, tz=timezone.utc).replace(tzinfo=None)
            if token_issued < user.password_changed_at:
                logger.warning("Token issued before password change rejected: user=%s", username)
                raise credentials_exception

    return user


def revoke_token(token: str, db: Session) -> None:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=settings.APP_NAME,
            issuer=settings.APP_NAME,
        )
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti:
            existing = db.query(TokenBlocklist).filter(TokenBlocklist.jti == jti).first()
            if existing:
                return
            blocked = TokenBlocklist(
                jti=jti,
                expires_at=datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None,
            )
            db.add(blocked)
            db.commit()
    except PyJWTError as e:
        logger.warning("Token revocation failed — invalid token: %s", str(e))


def cleanup_expired_tokens(db: Session) -> int:
    """Remove expired entries from the token blocklist."""
    now = datetime.now(timezone.utc)
    count = (
        db.query(TokenBlocklist)
        .filter(TokenBlocklist.expires_at < now)
        .delete(synchronize_session=False)
    )
    db.commit()
    return count
