from ..db.schemas import bank_account_schema
from ..core import exceptions
from ..db.model import bank_account_model
from sqlalchemy.orm import Session


def create_bank_account(db: Session, bank_data: bank_account_schema.BankAccountSchema) -> bank_account_schema.BankAccountResponse:
    new_bank_account = bank_account_model.BankAccount(
        bank_name=bank_data.bank_name,
        account_number=bank_data.account_number,
        account_name=bank_data.account_name,
        is_default=bank_data.is_default
    )

    db.add(new_bank_account)
    db.commit()
    db.refresh(new_bank_account)

    return bank_account_schema.BankAccountResponse.model_validate(new_bank_account)


def get_bank_account_by_id(db: Session, bank_account_id: str) -> bank_account_schema.BankAccountResponse:
    bank_account = db.query(bank_account_model.BankAccount).filter(
        bank_account_model.BankAccount.id == bank_account_id).first()

    if not bank_account:
        raise exceptions.NotFoundException("Bank account not found.")

    return bank_account_schema.BankAccountResponse.model_validate(bank_account)


def get_all_bank_accounts(db: Session) -> list[bank_account_schema.BankAccountResponse]:
    accounts = db.query(bank_account_model.BankAccount).all()
    return [bank_account_schema.BankAccountResponse.model_validate(a) for a in accounts]


def update_bank_account(db: Session, bank_account_id: str, bank_data: bank_account_schema.BankAccountSchema) -> bank_account_schema.BankAccountResponse:
    bank_account = db.query(bank_account_model.BankAccount).filter(
        bank_account_model.BankAccount.id == bank_account_id).first()

    if not bank_account:
        raise exceptions.NotFoundException("Bank account not found.")

    bank_account.bank_name = bank_data.bank_name
    bank_account.account_number = bank_data.account_number
    bank_account.account_name = bank_data.account_name
    bank_account.is_default = bank_data.is_default

    db.commit()
    db.refresh(bank_account)

    return bank_account_schema.BankAccountResponse.model_validate(bank_account)


def delete_bank_account(db: Session, bank_account_id: str):
    bank_account = db.query(bank_account_model.BankAccount).filter(
        bank_account_model.BankAccount.id == bank_account_id).first()

    if not bank_account:
        raise exceptions.NotFoundException("Bank account not found.")

    db.delete(bank_account)
    db.commit()
