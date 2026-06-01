import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...services import websocket_service

ws_router = APIRouter(tags=["WebSocket"])


@ws_router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    client_id = str(uuid.uuid4())
    await websocket_service.connect(ws, client_id)
    try:
        while True:
            # Keep connection alive; client can send pings
            await ws.receive_text()
    except WebSocketDisconnect:
        websocket_service.disconnect(client_id)
