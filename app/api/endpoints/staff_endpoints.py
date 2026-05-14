from fastapi import APIRouter
from ...core.dependencies import DBSession
from ...services import staff_service
from ...services.auth_service import CurrentStaff, AdminOnly
from ...db.schemas import staff_schema

staff_router = APIRouter(prefix="/staff", tags=["Staff"])


@staff_router.post("/", response_model=staff_schema.StaffResponse, dependencies=[])
def create_staff(data: staff_schema.StaffCreate, db: DBSession, _: AdminOnly):
    return staff_service.create_staff(db, data)


@staff_router.get("/me", response_model=staff_schema.StaffResponse)
def get_me(current_staff: CurrentStaff):
    return current_staff


@staff_router.get("/", response_model=list[staff_schema.StaffResponse])
def get_all_staff(db: DBSession, _: AdminOnly):
    return staff_service.get_all_staff(db)


@staff_router.get("/{staff_id}", response_model=staff_schema.StaffResponse)
def get_staff(staff_id: str, db: DBSession, _: CurrentStaff):
    return staff_service.get_staff_by_id(db, staff_id)


@staff_router.put("/{staff_id}", response_model=staff_schema.StaffResponse)
def update_staff(staff_id: str, data: staff_schema.StaffUpdate, db: DBSession, _: AdminOnly):
    return staff_service.update_staff(db, staff_id, data)


@staff_router.patch("/{staff_id}/password", status_code=204)
def change_password(staff_id: str, data: staff_schema.StaffChangePassword, db: DBSession, current_staff: CurrentStaff):
    if str(current_staff.id) != staff_id and current_staff.role != "admin":
        from ...core.exceptions import ForbiddenException
        raise ForbiddenException("You can only change your own password.")
    staff_service.change_password(db, staff_id, data)


@staff_router.delete("/{staff_id}", status_code=204)
def delete_staff(staff_id: str, db: DBSession, _: AdminOnly):
    staff_service.delete_staff(db, staff_id)
