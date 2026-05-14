from typing import Optional
from decimal import Decimal
import random
import string
from ..db.schemas import product_schema
from ..core import exceptions
from ..db.model import product_model
from sqlalchemy.orm import Session
import cloudinary.uploader
from ..core.config import CloudinaryConfig


def _extract_public_id(url: str) -> str:
    """Extract public_id from a Cloudinary secure_url."""
    parts = url.split("/upload/")[-1]
    # Remove version prefix (v123456/)
    if parts.startswith("v") and "/" in parts:
        parts = parts.split("/", 1)[1]
    # Remove file extension
    public_id = parts.rsplit(".", 1)[0]
    return public_id


def _delete_cloudinary_files(urls: list[str], resource_type: str = "image"):
    """Delete files from Cloudinary by their URLs."""
    for url in urls:
        public_id = _extract_public_id(url)
        cloudinary.uploader.destroy(public_id, resource_type=resource_type)


def _delete_product_media(product):
    """Delete all media associated with a product from Cloudinary."""
    if product.image_urls:
        _delete_cloudinary_files(product.image_urls, resource_type="image")
    if product.live_image_urls:
        _delete_cloudinary_files(product.live_image_urls, resource_type="image")
    if product.video_urls:
        _delete_cloudinary_files(product.video_urls, resource_type="video")
    if product.live_video_urls:
        _delete_cloudinary_files(product.live_video_urls, resource_type="video")
        
        


def upload_live_images(image_files: list) -> list[str]:
    uploaded_urls = []
    for image in image_files:
        result = cloudinary.uploader.upload(
            image, 
            folder="whatsapp_commerce/products/live_images",
            resource_type="image"
        )
        
        uploaded_urls.append(result["secure_url"])
        
    return uploaded_urls


def upload_live_videos(video_files: list) -> list[str]:
    uploaded_urls = []
    for video in video_files:
        result = cloudinary.uploader.upload(
            video, 
            folder="whatsapp_commerce/products/live_videos",
            resource_type="video"
        )
        
        uploaded_urls.append(result["secure_url"])
        
    return uploaded_urls


def upload_images(images: list) -> list[str]:
    uploaded_urls = []
    for image in images:
        result = cloudinary.uploader.upload(
            image, 
            folder="whatsapp_commerce/products/images",
            resource_type="image"
        )
        
        uploaded_urls.append(result["secure_url"])
        
    return uploaded_urls



def upload_videos(videos: list) -> list[str]:
    uploaded_urls = []
    for video in videos:
        result = cloudinary.uploader.upload(
            video, 
            folder="whatsapp_commerce/products/videos",
            resource_type="video"
        )
        
        uploaded_urls.append(result["secure_url"])
        
    return uploaded_urls


def create_product(db: Session, product_data: product_schema.ProductSchema) -> product_schema.ProductResponse:
    if product_data.sku:
        existing = db.query(product_model.Product).filter(
            product_model.Product.sku == product_data.sku
        ).first()
        if existing:
            raise exceptions.ConflictException("A product with this SKU already exists.")

    prefix = product_data.name[:4].upper()
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    tracking_id = f"{prefix}-{suffix}"
    
    image_urls = upload_images(product_data.image_urls) if product_data.image_urls else None
    live_image_urls = upload_live_images(product_data.live_image_urls) if product_data.live_image_urls else None
    video_urls = upload_videos(product_data.video_urls) if product_data.video_urls else None
    live_video_urls = upload_live_videos(product_data.live_video_urls) if product_data.live_video_urls else None

    new_product = product_model.Product(
        name=product_data.name,
        tracking_id=tracking_id,
        description=product_data.description,
        price=product_data.price,
        sku=product_data.sku,
        category_id=product_data.category_id,
        image_urls=image_urls,
        live_image_urls=live_image_urls,
        video_urls=video_urls,
        live_video_urls=live_video_urls,
        is_active=product_data.is_active
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    return product_schema.ProductResponse.model_validate(new_product)


def get_product_by_id(db: Session, product_id: str) -> product_schema.ProductResponse:
    product = db.query(product_model.Product).filter(
        product_model.Product.id == product_id,
        product_model.Product.is_active.is_(True)
        ).first()

    if not product:
        raise exceptions.NotFoundException("Product not found.")

    return product_schema.ProductResponse.model_validate(product)


def get_all_products(db: Session) -> list[product_schema.ProductResponse]:
    products = db.query(product_model.Product).filter(
        product_model.Product.is_active.is_(True)).all()
    return [product_schema.ProductResponse.model_validate(p) for p in products]


def get_product_by_sku(db: Session, sku: str) -> product_schema.ProductResponse:
    product = db.query(product_model.Product).filter(
        product_model.Product.sku == sku,
        product_model.Product.is_active.is_(True)).first()

    if not product:
        raise exceptions.NotFoundException("Product not found.")

    return product_schema.ProductResponse.model_validate(product)


def update_product(db: Session, product_id: str, product_data: product_schema.ProductSchema) -> product_schema.ProductResponse:
    product = db.query(product_model.Product).filter(
        product_model.Product.id == product_id).first()

    if not product:
        raise exceptions.NotFoundException("Product not found.")

    if product_data.sku:
        is_sku_taken = db.query(product_model.Product).filter(
            product_model.Product.sku == product_data.sku,
            product_model.Product.id != product_id
        ).first()
        if is_sku_taken:
            raise exceptions.ConflictException("SKU is already taken by another product.")

    if product_data.image_urls and product.image_urls:
        _delete_cloudinary_files(product.image_urls, resource_type="image")
    if product_data.live_image_urls and product.live_image_urls:
        _delete_cloudinary_files(product.live_image_urls, resource_type="image")
    if product_data.video_urls and product.video_urls:
        _delete_cloudinary_files(product.video_urls, resource_type="video")
    if product_data.live_video_urls and product.live_video_urls:
        _delete_cloudinary_files(product.live_video_urls, resource_type="video")


    image_urls = upload_images(product_data.image_urls) if product_data.image_urls else None
    live_image_urls = upload_live_images(product_data.live_image_urls) if product_data.live_image_urls else None
    video_urls = upload_videos(product_data.video_urls) if product_data.video_urls else None
    live_video_urls = upload_live_videos(product_data.live_video_urls) if product_data.live_video_urls else None

    product.name = product_data.name
    product.description = product_data.description
    product.price = product_data.price
    product.sku = product_data.sku
    product.category_id = product_data.category_id
    product.image_urls = image_urls
    product.live_image_urls = live_image_urls
    product.video_urls = video_urls
    product.live_video_urls = live_video_urls
    product.is_active = product_data.is_active

    db.commit()
    db.refresh(product)

    return product_schema.ProductResponse.model_validate(product)


def search_products(
    db: Session,
    name: Optional[str] = None,
    description: Optional[str] = None,
    category_id: Optional[str] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    is_active: Optional[bool] = None,
    sku: Optional[str] = None
) -> list[product_schema.ProductResponse]:
    query = db.query(product_model.Product)

    if name:
        query = query.filter(product_model.Product.name.ilike(f"%{name}%"))
    if category_id:
        query = query.filter(product_model.Product.category_id == category_id)
    if min_price is not None:
        query = query.filter(product_model.Product.price >= min_price)
    if max_price is not None:
        query = query.filter(product_model.Product.price <= max_price)
    if is_active is not None:
        query = query.filter(product_model.Product.is_active == is_active)
    if sku:
        query = query.filter(product_model.Product.sku == sku)
    if description:
        query = query.filter(product_model.Product.description.ilike(f"%{description}%"))
        
    products = query.all()
    return [product_schema.ProductResponse.model_validate(p) for p in products]


def delete_product(db: Session, product_id: str):
    product = db.query(product_model.Product).filter(
        product_model.Product.id == product_id).first()

    if not product:
        raise exceptions.NotFoundException("Product not found.")

    _delete_product_media(product)

    db.delete(product)
    db.commit()
