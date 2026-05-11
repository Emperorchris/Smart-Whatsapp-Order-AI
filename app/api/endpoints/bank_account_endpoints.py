from fastapi import APIRouter
from ...core.dependencies import DBSession
from ...services import bank_account_service
from ...db.schemas import bank_account_schema

bank_account_router = APIRouter(prefix="/bank-accounts", tags=["Bank Accounts"])


@bank_account_router.post("/", response_model=bank_account_schema.BankAccountResponse)
def create_bank_account(bank_data: bank_account_schema.BankAccountSchema, db: DBSession):
    return bank_account_service.create_bank_account(db, bank_data)


@bank_account_router.get("/", response_model=list[bank_account_schema.BankAccountResponse])
def get_all_bank_accounts(db: DBSession):
    return bank_account_service.get_all_bank_accounts(db)


@bank_account_router.get("/{bank_account_id}", response_model=bank_account_schema.BankAccountResponse)
def get_bank_account(bank_account_id: str, db: DBSession):
    return bank_account_service.get_bank_account_by_id(db, bank_account_id)


@bank_account_router.put("/{bank_account_id}", response_model=bank_account_schema.BankAccountResponse)
def update_bank_account(bank_account_id: str, bank_data: bank_account_schema.BankAccountSchema, db: DBSession):
    return bank_account_service.update_bank_account(db, bank_account_id, bank_data)


@bank_account_router.delete("/{bank_account_id}", status_code=204)
def delete_bank_account(bank_account_id: str, db: DBSession):
    bank_account_service.delete_bank_account(db, bank_account_id)
