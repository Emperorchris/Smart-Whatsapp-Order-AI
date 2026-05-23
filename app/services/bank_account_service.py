from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.schemas import bank_account_schema
from ..core import exceptions
from ..db.model import bank_account_model


async def create_bank_account(db: AsyncSession, bank_data: bank_account_schema.BankAccountSchema) -> bank_account_schema.BankAccountResponse:
    new_bank_account = bank_account_model.BankAccount(
        bank_name=bank_data.bank_name,
        account_number=bank_data.account_number,
        account_name=bank_data.account_name,
        is_default=bank_data.is_default
    )

    db.add(new_bank_account)
    await db.commit()
    await db.refresh(new_bank_account)

    return bank_account_schema.BankAccountResponse.model_validate(new_bank_account)


async def get_bank_account_by_id(db: AsyncSession, bank_account_id: str) -> bank_account_schema.BankAccountResponse:
    result = await db.execute(
        select(bank_account_model.BankAccount).filter(
            bank_account_model.BankAccount.id == bank_account_id
        )
    )
    bank_account = result.scalars().first()

    if not bank_account:
        raise exceptions.NotFoundException("Bank account not found.")

    return bank_account_schema.BankAccountResponse.model_validate(bank_account)


async def get_all_bank_accounts(db: AsyncSession) -> list[bank_account_schema.BankAccountResponse]:
    result = await db.execute(select(bank_account_model.BankAccount))
    accounts = result.scalars().all()
    return [bank_account_schema.BankAccountResponse.model_validate(a) for a in accounts]


async def update_bank_account(db: AsyncSession, bank_account_id: str, bank_data: bank_account_schema.BankAccountSchema) -> bank_account_schema.BankAccountResponse:
    result = await db.execute(
        select(bank_account_model.BankAccount).filter(
            bank_account_model.BankAccount.id == bank_account_id
        )
    )
    bank_account = result.scalars().first()

    if not bank_account:
        raise exceptions.NotFoundException("Bank account not found.")

    bank_account.bank_name = bank_data.bank_name
    bank_account.account_number = bank_data.account_number
    bank_account.account_name = bank_data.account_name
    bank_account.is_default = bank_data.is_default

    await db.commit()
    await db.refresh(bank_account)

    return bank_account_schema.BankAccountResponse.model_validate(bank_account)


async def delete_bank_account(db: AsyncSession, bank_account_id: str):
    result = await db.execute(
        select(bank_account_model.BankAccount).filter(
            bank_account_model.BankAccount.id == bank_account_id
        )
    )
    bank_account = result.scalars().first()

    if not bank_account:
        raise exceptions.NotFoundException("Bank account not found.")

    await db.delete(bank_account)
    await db.commit()
