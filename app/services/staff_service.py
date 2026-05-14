from sqlalchemy.orm import Session
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from ..db.schemas import staff_schema
from ..db.model import staff_model
from ..core import exceptions

pwd_context = PasswordHash([Argon2Hasher()])


def _hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_staff(db: Session, data: staff_schema.StaffCreate) -> staff_schema.StaffResponse:
    existing = db.query(staff_model.Staff).filter(staff_model.Staff.email == data.email).first()
    if existing:
        raise exceptions.ConflictException("A staff member with this email already exists.")

    new_staff = staff_model.Staff(
        name=data.name,
        email=data.email,
        phone_number=data.phone_number,
        role=data.role,
        password_hash=_hash_password(data.password),
    )

    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)

    return staff_schema.StaffResponse.model_validate(new_staff)


def get_staff_by_id(db: Session, staff_id: str) -> staff_schema.StaffResponse:
    staff = db.query(staff_model.Staff).filter(
        staff_model.Staff.id == staff_id,
        staff_model.Staff.is_active.is_(True)).first()
    if not staff:
        raise exceptions.NotFoundException("Staff member not found.")
    return staff_schema.StaffResponse.model_validate(staff)


def get_all_staff(db: Session) -> list[staff_schema.StaffResponse]:
    staff_list = db.query(staff_model.Staff).filter(
        staff_model.Staff.is_active.is_(True)).all()
    return [staff_schema.StaffResponse.model_validate(s) for s in staff_list]


def update_staff(db: Session, staff_id: str, data: staff_schema.StaffUpdate) -> staff_schema.StaffResponse:
    staff = db.query(staff_model.Staff).filter(staff_model.Staff.id == staff_id).first()
    if not staff:
        raise exceptions.NotFoundException("Staff member not found.")

    if data.email and data.email != staff.email:
        email_taken = db.query(staff_model.Staff).filter(
            staff_model.Staff.email == data.email,
            staff_model.Staff.id != staff_id
        ).first()
        if email_taken:
            raise exceptions.ConflictException("Email is already in use by another staff member.")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(staff, field, value)

    db.commit()
    db.refresh(staff)

    return staff_schema.StaffResponse.model_validate(staff)


def change_password(db: Session, staff_id: str, data: staff_schema.StaffChangePassword):
    staff = db.query(staff_model.Staff).filter(staff_model.Staff.id == staff_id).first()
    if not staff:
        raise exceptions.NotFoundException("Staff member not found.")

    if not _verify_password(data.current_password, staff.password_hash):
        raise exceptions.UnauthorizedException("Current password is incorrect.")

    staff.password_hash = _hash_password(data.new_password)
    db.commit()


def delete_staff(db: Session, staff_id: str):
    staff = db.query(staff_model.Staff).filter(staff_model.Staff.id == staff_id).first()
    if not staff:
        raise exceptions.NotFoundException("Staff member not found.")
    db.delete(staff)
    db.commit()


def authenticate_staff(db: Session, email: str, password: str) -> staff_model.Staff:
    """Returns the raw ORM object — used internally by auth_service."""
    staff = db.query(staff_model.Staff).filter(staff_model.Staff.email == email).first()
    if not staff or not _verify_password(password, staff.password_hash):
        raise exceptions.UnauthorizedException("Invalid email or password.")
    if not staff.is_active:
        raise exceptions.ForbiddenException("Account is inactive.")
    return staff
