from ..db.schemas import customers_schema
from ..core import exceptions
from ..db.model import customer_model
from sqlalchemy.orm import Session


def create_customer(db: Session, customer_data: customers_schema.CustomerSchema) -> customers_schema.CustomerResponse:
    new_customer = customer_model.Customer(
        name=customer_data.name,
        whatsapp_number=customer_data.whatsapp_number,
        email=customer_data.email,
        display_name=customer_data.display_name,
        extra_metadata=customer_data.extra_metadata
    )

    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)

    return customers_schema.CustomerResponse.model_validate(new_customer)


def get_customer_by_id(db: Session, customer_id: str) -> customers_schema.CustomerResponse:
    customer = db.query(customer_model.Customer).filter(
        customer_model.Customer.id == customer_id).first()

    if not customer:
        raise exceptions.NotFoundException("Customer not found.")

    return customers_schema.CustomerResponse.model_validate(customer)


def get_customer_by_whatsapp_number(db: Session, whatsapp_number: str) -> customers_schema.CustomerResponse:
    customer = db.query(customer_model.Customer).filter(
        customer_model.Customer.whatsapp_number == whatsapp_number).first()

    if not customer:
        raise exceptions.NotFoundException("Customer not found.")

    return customers_schema.CustomerResponse.model_validate(customer)


def update_customer(db: Session, customer_id: str, customer_data: customers_schema.CustomerSchema) -> customers_schema.CustomerResponse:
    customer = db.query(customer_model.Customer).filter(
        customer_model.Customer.id == customer_id).first()

    if not customer:
        raise exceptions.NotFoundException("Customer not found.")
    
    is_number_exist = db.query(customer_model.Customer).filter(
        customer_model.Customer.whatsapp_number == customer_data.whatsapp_number,
        customer_model.Customer.id != customer_id
    ).first()

    if is_number_exist:
        raise exceptions.ConflictException("WhatsApp number is already associated with another customer.")

    customer.name = customer_data.name
    customer.whatsapp_number = customer_data.whatsapp_number
    customer.display_name = customer_data.display_name
    customer.extra_metadata = customer_data.extra_metadata

    db.commit()
    db.refresh(customer)

    return customers_schema.CustomerResponse.model_validate(customer)


def delete_customer(db: Session, customer_id: str):
    customer = db.query(customer_model.Customer).filter(
        customer_model.Customer.id == customer_id).first()

    if not customer:
        raise exceptions.NotFoundException("Customer not found.")

    db.delete(customer)
    db.commit()