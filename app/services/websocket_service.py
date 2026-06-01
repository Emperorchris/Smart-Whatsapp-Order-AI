"""
WebSocket connection manager for real-time admin dashboard updates.

Events pushed to connected clients:
- new_order, order_status_changed
- new_handoff, handoff_claimed, handoff_resolved
- new_customer
- low_stock_alert
"""

import json
from datetime import datetime, timezone
from fastapi import WebSocket

_connections: dict[str, WebSocket] = {}


async def connect(ws: WebSocket, client_id: str):
    await ws.accept()
    _connections[client_id] = ws


def disconnect(client_id: str):
    _connections.pop(client_id, None)


async def broadcast(event: str, data: dict):
    payload = json.dumps({
        "event": event,
        "data": data,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    })
    dead = []
    for cid, ws in _connections.items():
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(cid)
    for cid in dead:
        _connections.pop(cid, None)


async def send_to(client_id: str, event: str, data: dict):
    ws = _connections.get(client_id)
    if ws:
        try:
            await ws.send_text(json.dumps({
                "event": event,
                "data": data,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }))
        except Exception:
            _connections.pop(client_id, None)


def active_count() -> int:
    return len(_connections)
