from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class BankAccountSchema(BaseModel):
    bank_name: str
    account_number: str
    account_name: str
    is_default: bool = False


class BankAccountResponse(BankAccountSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
