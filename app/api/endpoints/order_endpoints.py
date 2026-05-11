from fastapi import APIRouter
from ...core.dependencies import DBSession
from ...services import order_service, order_item_service
from ...db.schemas import order_schema, order_item_schema

order_router = APIRouter(prefix="/orders", tags=["Orders"])


# Order routes

@order_router.post("/", response_model=order_schema.OrderResponse)
def create_order(order_data: order_schema.OrderSchema, db: DBSession):
    return order_service.create_order(db, order_data)


@order_router.get("/", response_model=list[order_schema.OrderResponse])
def get_all_orders(db: DBSession):
    return order_service.get_all_orders(db)


@order_router.get("/{order_id}", response_model=order_schema.OrderResponse)
def get_order(order_id: str, db: DBSession):
    return order_service.get_order_by_id(db, order_id)


@order_router.get("/number/{order_number}", response_model=order_schema.OrderResponse)
def get_order_by_number(order_number: str, db: DBSession):
    return order_service.get_order_by_order_number(db, order_number)


@order_router.get("/customer/{customer_id}", response_model=list[order_schema.OrderResponse])
def get_orders_by_customer(customer_id: str, db: DBSession):
    return order_service.get_orders_by_customer_id(db, customer_id)


@order_router.put("/{order_id}", response_model=order_schema.OrderResponse)
def update_order(order_id: str, order_data: order_schema.OrderSchema, db: DBSession):
    return order_service.update_order(db, order_id, order_data)


@order_router.delete("/{order_id}", status_code=204)
def delete_order(order_id: str, db: DBSession):
    order_service.delete_order(db, order_id)


# Order item routes

@order_router.post("/{order_id}/items", response_model=order_item_schema.OrderItemResponse)
def create_order_item(order_id: str, order_item_data: order_item_schema.OrderItemSchema, db: DBSession):
    return order_item_service.create_order_item(db, order_item_data)


@order_router.get("/{order_id}/items", response_model=list[order_item_schema.OrderItemResponse])
def get_order_items(order_id: str, db: DBSession):
    return order_item_service.get_order_items_by_order_id(db, order_id)


@order_router.get("/{order_id}/items/{order_item_id}", response_model=order_item_schema.OrderItemResponse)
def get_order_item(order_id: str, order_item_id: str, db: DBSession):
    return order_item_service.get_order_item_by_id(db, order_item_id)


@order_router.put("/{order_id}/items/{order_item_id}", response_model=order_item_schema.OrderItemResponse)
def update_order_item(order_id: str, order_item_id: str, order_item_data: order_item_schema.OrderItemSchema, db: DBSession):
    return order_item_service.update_order_item(db, order_item_id, order_item_data)


@order_router.delete("/{order_id}/items/{order_item_id}", status_code=204)
def delete_order_item(order_id: str, order_item_id: str, db: DBSession):
    order_item_service.delete_order_item(db, order_item_id)
