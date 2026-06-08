from fastapi import APIRouter, Query
from pydantic import BaseModel
from ...core.dependencies import DBSession
from ...services import order_service, order_item_service, order_tracking_service
from ...services.auth_service import CurrentStaff, AdminOnly
from ...db.schemas import order_schema, order_item_schema, customer_address_schema, order_status_history_schema
from ...core import utils


class UpdateStatusBody(BaseModel):
    status: utils.OrderStatus

order_router = APIRouter(prefix="/orders", tags=["Orders"])


# Order routes

@order_router.post("/", response_model=order_schema.OrderResponse)
async def create_order(order_data: order_schema.OrderSchema, db: DBSession, _: CurrentStaff):
    return await order_service.create_order(db, order_data)


@order_router.get("/", response_model=list[order_schema.OrderResponse])
async def get_all_orders(
    db: DBSession,
    _: CurrentStaff,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    return await order_service.get_all_orders(db, skip=skip, limit=limit)


@order_router.patch("/bulk/status", response_model=order_schema.BulkOrderStatusResponse)
async def bulk_update_order_status(body: order_schema.BulkOrderStatusUpdate, db: DBSession, _: AdminOnly):
    return await order_service.bulk_update_order_status(db, body.order_ids, body.status)


@order_router.get("/{order_id}", response_model=order_schema.OrderResponse)
async def get_order(order_id: str, db: DBSession, _: CurrentStaff):
    return await order_service.get_order_by_id(db, order_id)


@order_router.get("/number/{order_number}", response_model=order_schema.OrderResponse)
async def get_order_by_number(order_number: str, db: DBSession, _: CurrentStaff):
    return await order_service.get_order_by_order_number(db, order_number)


@order_router.get("/customer/{customer_id}", response_model=list[order_schema.OrderResponse])
async def get_orders_by_customer(customer_id: str, db: DBSession, _: CurrentStaff):
    return await order_service.get_orders_by_customer_id(db, customer_id)


@order_router.put("/{order_id}", response_model=order_schema.OrderResponse)
async def update_order(order_id: str, order_data: order_schema.OrderSchema, db: DBSession, _: CurrentStaff):
    return await order_service.update_order(db, order_id, order_data)


@order_router.patch("/{order_id}/status", response_model=order_schema.OrderResponse)
async def update_order_status(order_id: str, body: order_schema.UpdateOrderStatusWithDetails, db: DBSession, _: CurrentStaff):
    return await order_tracking_service.update_status_with_tracking(db, order_id, body)


@order_router.get("/{order_id}/timeline", response_model=list[order_status_history_schema.OrderStatusHistoryResponse])
async def get_order_timeline(order_id: str, db: DBSession, _: CurrentStaff):
    return await order_tracking_service.get_order_timeline(db, order_id)


@order_router.patch("/{order_id}/address", response_model=order_schema.OrderResponse)
async def update_order_address(order_id: str, address_data: customer_address_schema.CustomerAddressSchema, db: DBSession, _: CurrentStaff):
    return await order_service.update_order_address(db, order_id, address_data)


@order_router.patch("/{order_id}/cancel", response_model=order_schema.OrderResponse)
async def cancel_order(order_id: str, db: DBSession, _: CurrentStaff):
    return await order_service.cancel_order(db, order_id)


@order_router.delete("/{order_id}", status_code=204)
async def delete_order(order_id: str, db: DBSession, _: AdminOnly):
    await order_service.delete_order(db, order_id)


# Order item routes

@order_router.post("/{order_id}/items", response_model=order_item_schema.OrderItemResponse)
async def create_order_item(order_id: str, order_item_data: order_item_schema.OrderItemSchema, db: DBSession, _: CurrentStaff):
    return await order_item_service.create_order_item(db, order_item_data)


@order_router.get("/{order_id}/items", response_model=list[order_item_schema.OrderItemResponse])
async def get_order_items(order_id: str, db: DBSession, _: CurrentStaff):
    return await order_item_service.get_order_items_by_order_id(db, order_id)


@order_router.get("/{order_id}/items/{order_item_id}", response_model=order_item_schema.OrderItemResponse)
async def get_order_item(order_id: str, order_item_id: str, db: DBSession, _: CurrentStaff):
    return await order_item_service.get_order_item_by_id(db, order_item_id)


@order_router.put("/{order_id}/items/{order_item_id}", response_model=order_item_schema.OrderItemResponse)
async def update_order_item(order_id: str, order_item_id: str, order_item_data: order_item_schema.OrderItemSchema, db: DBSession, _: CurrentStaff):
    return await order_item_service.update_order_item(db, order_item_id, order_item_data)


@order_router.patch("/{order_id}/items/{order_item_id}/delivery-status", response_model=order_item_schema.OrderItemResponse)
async def update_item_delivery_status(order_id: str, order_item_id: str, body: order_schema.UpdateItemDeliveryStatus, db: DBSession, _: CurrentStaff):
    return await order_tracking_service.update_item_delivery_status(db, order_id, order_item_id, body)


@order_router.delete("/{order_id}/items/{order_item_id}", status_code=204)
async def delete_order_item(order_id: str, order_item_id: str, db: DBSession, _: AdminOnly):
    await order_item_service.delete_order_item(db, order_item_id)
