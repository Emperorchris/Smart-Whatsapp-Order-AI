from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.schemas import customers_schema
from ..core import exceptions
from ..db.model import customer_model


async def create_customer(db: AsyncSession, customer_data: customers_schema.CustomerSchema) -> customers_schema.CustomerResponse:
    new_customer = customer_model.Customer(
        name=customer_data.name,
        whatsapp_number=customer_data.whatsapp_number,
        email=customer_data.email,
        display_name=customer_data.display_name,
        extra_metadata=customer_data.extra_metadata
    )

    db.add(new_customer)
    await db.commit()
    await db.refresh(new_customer)

    return customers_schema.CustomerResponse.model_validate(new_customer)


async def get_customer_by_id(db: AsyncSession, customer_id: str) -> customers_schema.CustomerResponse:
    result = await db.execute(
        select(customer_model.Customer).filter(customer_model.Customer.id == customer_id)
    )
    customer = result.scalars().first()

    if not customer:
        raise exceptions.NotFoundException("Customer not found.")

    return customers_schema.CustomerResponse.model_validate(customer)


async def get_customer_by_whatsapp_number(db: AsyncSession, whatsapp_number: str) -> customers_schema.CustomerResponse:
    result = await db.execute(
        select(customer_model.Customer).filter(
            customer_model.Customer.whatsapp_number == whatsapp_number
        )
    )
    customer = result.scalars().first()

    if not customer:
        raise exceptions.NotFoundException("Customer not found.")

    return customers_schema.CustomerResponse.model_validate(customer)


async def update_customer(db: AsyncSession, customer_id: str, customer_data: customers_schema.CustomerSchema) -> customers_schema.CustomerResponse:
    result = await db.execute(
        select(customer_model.Customer).filter(customer_model.Customer.id == customer_id)
    )
    customer = result.scalars().first()

    if not customer:
        raise exceptions.NotFoundException("Customer not found.")

    dup_result = await db.execute(
        select(customer_model.Customer).filter(
            customer_model.Customer.whatsapp_number == customer_data.whatsapp_number,
            customer_model.Customer.id != customer_id
        )
    )
    if dup_result.scalars().first():
        raise exceptions.ConflictException("WhatsApp number is already associated with another customer.")

    customer.name = customer_data.name
    customer.whatsapp_number = customer_data.whatsapp_number
    customer.display_name = customer_data.display_name
    customer.extra_metadata = customer_data.extra_metadata

    await db.commit()
    await db.refresh(customer)

    return customers_schema.CustomerResponse.model_validate(customer)


async def delete_customer(db: AsyncSession, customer_id: str):
    result = await db.execute(
        select(customer_model.Customer).filter(customer_model.Customer.id == customer_id)
    )
    customer = result.scalars().first()

    if not customer:
        raise exceptions.NotFoundException("Customer not found.")

    await db.delete(customer)
    await db.commit()
