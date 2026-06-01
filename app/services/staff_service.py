from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from ..db.schemas import staff_schema
from ..db.model import staff_model
from ..core import exceptions

pwd_context = PasswordHash([Argon2Hasher()])


def _normalize_whatsapp_number(number: str | None) -> str | None:
    """Normalize WhatsApp number to international format (no + prefix).
    Handles: +234..., 234..., 0803..., 803..."""
    if not number:
        return number
    value = number.strip().lstrip("+")
    if value.startswith("0") and len(value) >= 10:
        value = "234" + value[1:]
    elif not value.startswith("234") and len(value) >= 9:
        value = "234" + value
    return value


def _hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def create_staff(db: AsyncSession, data: staff_schema.StaffCreate) -> staff_schema.StaffResponse:
    result = await db.execute(
        select(staff_model.Staff).filter(staff_model.Staff.email == data.email)
    )
    if result.scalars().first():
        raise exceptions.ConflictException("A staff member with this email already exists.")

    new_staff = staff_model.Staff(
        name=data.name,
        email=data.email,
        phone_number=data.phone_number,
        whatsapp_number=_normalize_whatsapp_number(data.whatsapp_number),
        role=data.role,
        password_hash=_hash_password(data.password),
    )

    db.add(new_staff)
    await db.commit()
    await db.refresh(new_staff)

    return staff_schema.StaffResponse.model_validate(new_staff)


async def get_staff_by_id(db: AsyncSession, staff_id: str) -> staff_schema.StaffResponse:
    result = await db.execute(
        select(staff_model.Staff).filter(
            staff_model.Staff.id == staff_id,
            staff_model.Staff.is_active.is_(True)
        )
    )
    staff = result.scalars().first()
    if not staff:
        raise exceptions.NotFoundException("Staff member not found.")
    return staff_schema.StaffResponse.model_validate(staff)


async def get_all_staff(db: AsyncSession) -> list[staff_schema.StaffResponse]:
    result = await db.execute(
        select(staff_model.Staff).filter(staff_model.Staff.is_active.is_(True))
    )
    staff_list = result.scalars().all()
    return [staff_schema.StaffResponse.model_validate(s) for s in staff_list]


async def update_staff(db: AsyncSession, staff_id: str, data: staff_schema.StaffUpdate) -> staff_schema.StaffResponse:
    result = await db.execute(
        select(staff_model.Staff).filter(staff_model.Staff.id == staff_id)
    )
    staff = result.scalars().first()
    if not staff:
        raise exceptions.NotFoundException("Staff member not found.")

    if data.email and data.email != staff.email:
        dup_result = await db.execute(
            select(staff_model.Staff).filter(
                staff_model.Staff.email == data.email,
                staff_model.Staff.id != staff_id
            )
        )
        if dup_result.scalars().first():
            raise exceptions.ConflictException("Email is already in use by another staff member.")

    update_data = data.model_dump(exclude_unset=True)
    if "whatsapp_number" in update_data:
        update_data["whatsapp_number"] = _normalize_whatsapp_number(update_data["whatsapp_number"])
    for field, value in update_data.items():
        setattr(staff, field, value)

    await db.commit()
    await db.refresh(staff)

    return staff_schema.StaffResponse.model_validate(staff)


async def change_password(db: AsyncSession, staff_id: str, data: staff_schema.StaffChangePassword):
    result = await db.execute(
        select(staff_model.Staff).filter(staff_model.Staff.id == staff_id)
    )
    staff = result.scalars().first()
    if not staff:
        raise exceptions.NotFoundException("Staff member not found.")

    if not _verify_password(data.current_password, staff.password_hash):
        raise exceptions.UnauthorizedException("Current password is incorrect.")

    staff.password_hash = _hash_password(data.new_password)
    await db.commit()


async def delete_staff(db: AsyncSession, staff_id: str):
    result = await db.execute(
        select(staff_model.Staff).filter(staff_model.Staff.id == staff_id)
    )
    staff = result.scalars().first()
    if not staff:
        raise exceptions.NotFoundException("Staff member not found.")
    await db.delete(staff)
    await db.commit()


async def authenticate_staff(db: AsyncSession, email: str, password: str) -> staff_model.Staff:
    result = await db.execute(
        select(staff_model.Staff).filter(staff_model.Staff.email == email)
    )
    staff = result.scalars().first()
    if not staff or not _verify_password(password, staff.password_hash):
        raise exceptions.UnauthorizedException("Invalid email or password.")
    if not staff.is_active:
        raise exceptions.ForbiddenException("Account is inactive.")
    return staff
