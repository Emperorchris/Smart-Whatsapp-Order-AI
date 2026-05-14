from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from sqlalchemy.orm import Session
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from ..core.config import Config
from ..core import exceptions
from ..db.db_engine import get_db
from ..db.model import staff_model
from ..db.schemas import staff_schema
from . import staff_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

_token_hasher = PasswordHash([Argon2Hasher()])


def _hash_token(token: str) -> str:
    return _token_hasher.hash(token)


def _verify_token_hash(token: str, token_hash: str) -> bool:
    return _token_hasher.verify(token, token_hash)


def create_access_token(staff_id: str, role: str) -> str:
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(staff_id), "role": role, "exp": expire, "type": "access"}
    return jwt.encode(payload, Config.SECRET_KEY, algorithm=Config.ALGORITHM)


def create_refresh_token(staff_id: str) -> str:
    expire = datetime.now(tz=timezone.utc) + timedelta(days=Config.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(staff_id), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, Config.SECRET_KEY, algorithm=Config.ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
        if payload.get("type") != "access":
            raise exceptions.UnauthorizedException("Invalid token type.")
        return payload
    except jwt.PyJWTError:
        raise exceptions.UnauthorizedException("Invalid or expired token.")


def get_current_staff(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> staff_schema.StaffResponse:
    payload = decode_access_token(token)
    staff_id: str = payload.get("sub")
    if not staff_id:
        raise exceptions.UnauthorizedException("Invalid token payload.")

    staff = db.query(staff_model.Staff).filter(staff_model.Staff.id == staff_id).first()
    if not staff:
        raise exceptions.UnauthorizedException("Staff member no longer exists.")
    if not staff.is_active:
        raise exceptions.ForbiddenException("Account is inactive.")

    return staff_schema.StaffResponse.model_validate(staff)


def require_admin(
    current_staff: Annotated[staff_schema.StaffResponse, Depends(get_current_staff)],
) -> staff_schema.StaffResponse:
    if current_staff.role != "admin":
        raise exceptions.ForbiddenException("Unauthorized access.")
    return current_staff


def login(db: Session, credentials: staff_schema.StaffLoginSchema) -> staff_schema.TokenResponse:
    staff = staff_service.authenticate_staff(db, credentials.email, credentials.password)

    access_token = create_access_token(str(staff.id), staff.role)
    refresh_token = create_refresh_token(str(staff.id))

    staff.refresh_token_hash = _hash_token(refresh_token)
    db.commit()

    return staff_schema.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        staff=staff_schema.StaffResponse.model_validate(staff),
    )


def refresh(db: Session, data: staff_schema.RefreshTokenSchema) -> staff_schema.TokenResponse:
    try:
        payload = jwt.decode(data.refresh_token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
        if payload.get("type") != "refresh":
            raise exceptions.UnauthorizedException("Invalid token type.")
    except jwt.PyJWTError:
        raise exceptions.UnauthorizedException("Invalid or expired refresh token.")

    staff_id: str = payload.get("sub")
    staff = db.query(staff_model.Staff).filter(staff_model.Staff.id == staff_id).first()

    if not staff or not staff.refresh_token_hash:
        raise exceptions.UnauthorizedException("Refresh token has been revoked.")
    if not staff.is_active:
        raise exceptions.ForbiddenException("Account is inactive.")
    if not _verify_token_hash(data.refresh_token, staff.refresh_token_hash):
        raise exceptions.UnauthorizedException("Refresh token mismatch.")

    # Rotate: issue new tokens and store new hash
    access_token = create_access_token(str(staff.id), staff.role)
    new_refresh_token = create_refresh_token(str(staff.id))

    staff.refresh_token_hash = _hash_token(new_refresh_token)
    db.commit()

    return staff_schema.TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        staff=staff_schema.StaffResponse.model_validate(staff),
    )


def logout(db: Session, staff_id: str):
    staff = db.query(staff_model.Staff).filter(staff_model.Staff.id == staff_id).first()
    if staff:
        staff.refresh_token_hash = None
        db.commit()


# Reusable dependency type aliases
CurrentStaff = Annotated[staff_schema.StaffResponse, Depends(get_current_staff)]
AdminOnly = Annotated[staff_schema.StaffResponse, Depends(require_admin)]
