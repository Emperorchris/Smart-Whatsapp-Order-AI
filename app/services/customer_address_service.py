from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.schemas import customer_address_schema
from ..core import exceptions
from ..db.model import customer_address_model


async def create_address(db: AsyncSession, address_data: customer_address_schema.CustomerAddressSchema) -> customer_address_schema.CustomerAddressResponse:
    if address_data.is_default:
        await _unset_default(db, str(address_data.customer_id))

    new_address = customer_address_model.CustomerAddress(
        customer_id=address_data.customer_id,
        label=address_data.label,
        full_name=address_data.full_name,
        phone_number=address_data.phone_number,
        address_line=address_data.address_line,
        city=address_data.city,
        state=address_data.state,
        country=address_data.country,
        postal_code=address_data.postal_code,
        landmark=address_data.landmark,
        is_default=address_data.is_default,
    )

    db.add(new_address)
    await db.commit()
    await db.refresh(new_address)

    return customer_address_schema.CustomerAddressResponse.model_validate(new_address)


async def get_address_by_id(db: AsyncSession, address_id: str) -> customer_address_schema.CustomerAddressResponse:
    result = await db.execute(
        select(customer_address_model.CustomerAddress).filter(
            customer_address_model.CustomerAddress.id == address_id
        )
    )
    address = result.scalars().first()

    if not address:
        raise exceptions.NotFoundException("Address not found.")

    return customer_address_schema.CustomerAddressResponse.model_validate(address)


async def get_addresses_by_customer_id(db: AsyncSession, customer_id: str) -> list[customer_address_schema.CustomerAddressResponse]:
    result = await db.execute(
        select(customer_address_model.CustomerAddress).filter(
            customer_address_model.CustomerAddress.customer_id == customer_id
        )
    )
    addresses = result.scalars().all()
    return [customer_address_schema.CustomerAddressResponse.model_validate(a) for a in addresses]


async def get_default_address(db: AsyncSession, customer_id: str) -> customer_address_schema.CustomerAddressResponse:
    result = await db.execute(
        select(customer_address_model.CustomerAddress).filter(
            customer_address_model.CustomerAddress.customer_id == customer_id,
            customer_address_model.CustomerAddress.is_default.is_(True),
        )
    )
    address = result.scalars().first()

    if not address:
        raise exceptions.NotFoundException("No default address found.")

    return customer_address_schema.CustomerAddressResponse.model_validate(address)


async def update_address(db: AsyncSession, address_id: str, address_data: customer_address_schema.CustomerAddressSchema) -> customer_address_schema.CustomerAddressResponse:
    result = await db.execute(
        select(customer_address_model.CustomerAddress).filter(
            customer_address_model.CustomerAddress.id == address_id
        )
    )
    address = result.scalars().first()

    if not address:
        raise exceptions.NotFoundException("Address not found.")

    if address_data.is_default:
        await _unset_default(db, str(address_data.customer_id))

    address.label = address_data.label
    address.full_name = address_data.full_name
    address.phone_number = address_data.phone_number
    address.address_line = address_data.address_line
    address.city = address_data.city
    address.state = address_data.state
    address.country = address_data.country
    address.postal_code = address_data.postal_code
    address.landmark = address_data.landmark
    address.is_default = address_data.is_default

    await db.commit()
    await db.refresh(address)

    return customer_address_schema.CustomerAddressResponse.model_validate(address)



async def set_default_address(db: AsyncSession, address_id: str) -> customer_address_schema.CustomerAddressResponse:
    result = await db.execute(
        select(customer_address_model.CustomerAddress).filter(
            customer_address_model.CustomerAddress.id == address_id
        )
    )
    address = result.scalars().first()

    if not address:
        raise exceptions.NotFoundException("Address not found.")

    await _unset_default(db, str(address.customer_id))

    address.is_default = True
    await db.commit()
    await db.refresh(address)

    return customer_address_schema.CustomerAddressResponse.model_validate(address)



async def delete_address(db: AsyncSession, address_id: str):
    result = await db.execute(
        select(customer_address_model.CustomerAddress).filter(
            customer_address_model.CustomerAddress.id == address_id
        )
    )
    address = result.scalars().first()

    if not address:
        raise exceptions.NotFoundException("Address not found.")

    await db.delete(address)
    await db.commit()


async def _unset_default(db: AsyncSession, customer_id: str):
    """Unset the current default address for a customer before setting a new one."""
    result = await db.execute(
        select(customer_address_model.CustomerAddress).filter(
            customer_address_model.CustomerAddress.customer_id == customer_id,
            customer_address_model.CustomerAddress.is_default.is_(True),
        )
    )
    current_default = result.scalars().first()
    if current_default:
        current_default.is_default = False
