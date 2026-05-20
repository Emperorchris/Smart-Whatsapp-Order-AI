from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from ...core.dependencies import DBSession
from ...services import auth_service
from ...db.schemas import staff_schema

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.post("/login", response_model=staff_schema.TokenResponse)
def login(db: DBSession, form_data: OAuth2PasswordRequestForm = Depends()):
    credentials = staff_schema.StaffLoginSchema(email=form_data.username, password=form_data.password)
    return auth_service.login(db, credentials)


@auth_router.post("/refresh", response_model=staff_schema.TokenResponse)
def refresh(data: staff_schema.RefreshTokenSchema, db: DBSession):
    return auth_service.refresh(db, data)


@auth_router.post("/logout", status_code=204)
def logout(current_staff: auth_service.CurrentStaff, db: DBSession):
    auth_service.logout(db, str(current_staff.id))
