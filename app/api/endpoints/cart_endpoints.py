from fastapi import APIRouter
from ...core.dependencies import DBSession
from ...services import cart_service, cart_item_service
from ...db.schemas import cart_schema, cart_item_schema

cart_router = APIRouter(prefix="/carts", tags=["Carts"])


# Cart routes

@cart_router.post("/", response_model=cart_schema.CartResponse)
def create_cart(cart_data: cart_schema.CartSchema, db: DBSession):
    return cart_service.create_cart(db, cart_data)


@cart_router.get("/", response_model=list[cart_schema.CartResponse])
def get_all_carts(db: DBSession):
    return cart_service.get_all_carts(db)


@cart_router.get("/{cart_id}", response_model=cart_schema.CartResponse)
def get_cart(cart_id: str, db: DBSession):
    return cart_service.get_cart_by_id(db, cart_id)


@cart_router.get("/customer/{customer_id}", response_model=list[cart_schema.CartResponse])
def get_carts_by_customer(customer_id: str, db: DBSession):
    return cart_service.get_carts_by_customer_id(db, customer_id)


@cart_router.put("/{cart_id}", response_model=cart_schema.CartResponse)
def update_cart(cart_id: str, cart_data: cart_schema.CartSchema, db: DBSession):
    return cart_service.update_cart(db, cart_id, cart_data)


@cart_router.delete("/{cart_id}", status_code=204)
def delete_cart(cart_id: str, db: DBSession):
    cart_service.delete_cart(db, cart_id)


# Cart item routes

@cart_router.post("/{cart_id}/items", response_model=cart_item_schema.CartItemResponse)
def create_cart_item(cart_id: str, cart_item_data: cart_item_schema.CartItemSchema, db: DBSession):
    return cart_item_service.create_cart_item(db, cart_item_data)


@cart_router.get("/{cart_id}/items", response_model=list[cart_item_schema.CartItemResponse])
def get_cart_items(cart_id: str, db: DBSession):
    return cart_item_service.get_cart_items_by_cart_id(db, cart_id)


@cart_router.get("/{cart_id}/items/{cart_item_id}", response_model=cart_item_schema.CartItemResponse)
def get_cart_item(cart_id: str, cart_item_id: str, db: DBSession):
    return cart_item_service.get_cart_item_by_id(db, cart_item_id)


@cart_router.put("/{cart_id}/items/{cart_item_id}", response_model=cart_item_schema.CartItemResponse)
def update_cart_item(cart_id: str, cart_item_id: str, cart_item_data: cart_item_schema.CartItemSchema, db: DBSession):
    return cart_item_service.update_cart_item(db, cart_item_id, cart_item_data)


@cart_router.delete("/{cart_id}/items/{cart_item_id}", status_code=204)
def delete_cart_item(cart_id: str, cart_item_id: str, db: DBSession):
    cart_item_service.delete_cart_item(db, cart_item_id)
