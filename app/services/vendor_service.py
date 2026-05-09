from ..db.schemas import vendor_schema
from ..core import exceptions
from ..db.model import vendor_model
from sqlalchemy.orm import Session

def create_vendor(db: Session, vendor_data: vendor_schema.VendorCreate) -> vendor_schema.VendorResponse:
    # Check if a vendor with the same slug or WhatsApp number already exists
    existing_vendor = db.query(vendor_model.Vendor).filter(
        (vendor_model.Vendor.slug == vendor_data.slug) |
        (vendor_model.Vendor.whatsapp_number == vendor_data.whatsapp_number)
    ).first()

    if existing_vendor:
        raise exceptions.ConflictException(
            "A vendor with the same slug or WhatsApp number already exists.")

    new_vendor = vendor_model.Vendor(
        name=vendor_data.name,
        slug=vendor_data.slug,
        whatsapp_number=vendor_data.whatsapp_number,
        description=vendor_data.description,
        routing_keywords=vendor_data.routing_keywords,
        settings=vendor_data.settings
    )

    db.add(new_vendor)
    db.commit()
    db.refresh(new_vendor)

    return vendor_schema.VendorResponse.model_validate(new_vendor)


def update_vendor(db: Session, vendor_id: str, vendor_data: vendor_schema.VendorUpdate) -> vendor_schema.VendorResponse:
    vendor = db.query(vendor_model.Vendor).filter(
        vendor_model.Vendor.id == vendor_id).first()

    if not vendor:
        raise exceptions.NotFoundException("Vendor not found.")
    
    is_slug_taken = db.query(vendor_model.Vendor).filter(
        vendor_model.Vendor.slug == vendor_data.slug,
        vendor_model.Vendor.id != vendor_id
    ).first()

    if is_slug_taken:
        raise exceptions.ConflictException("Slug is already taken by another vendor.")

    vendor.name = vendor_data.name or vendor.name
    vendor.slug = vendor_data.slug or vendor.slug
    vendor.whatsapp_number = vendor_data.whatsapp_number or vendor.whatsapp_number
    vendor.description = vendor_data.description or vendor.description
    vendor.routing_keywords = vendor_data.routing_keywords or vendor.routing_keywords
    vendor.settings = vendor_data.settings or vendor.settings
    vendor.active = vendor_data.active if vendor_data.active is not None else vendor.active

    db.commit()
    db.refresh(vendor)

    return vendor_schema.VendorResponse.model_validate(vendor)



def get_vendor(db: Session, vendor_id: str) -> vendor_schema.VendorResponse:
    vendor = db.query(vendor_model.Vendor).filter(
        vendor_model.Vendor.id == vendor_id).first()

    if not vendor:
        raise exceptions.NotFoundException("Vendor not found.")

    return vendor_schema.VendorResponse.model_validate(vendor)


def get_all_vendors(db: Session) -> list[vendor_schema.VendorResponse]:
    vendors = db.query(vendor_model.Vendor).all()
    return [vendor_schema.VendorResponse.model_validate(vendor) for vendor in vendors]


def delete_vendor(db: Session, vendor_id: str) -> None:
    vendor = db.query(vendor_model.Vendor).filter(
        vendor_model.Vendor.id == vendor_id).first()

    if not vendor:
        raise exceptions.NotFoundException("Vendor not found.")

    db.delete(vendor)
    db.commit()