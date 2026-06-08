from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .core import Config
from .core.exceptions import register_exception_handlers
from .core.rate_limiter import limiter
from .api.router import api_router
from .api.endpoints.websocket_endpoints import ws_router
from .db.db_engine import AsyncSessionLocal
from sqlalchemy import text


app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router)


@app.get("/")
def root():
    return {"message": "Welcome to the WhatsApp Commerce API!"}


@app.get("/health")
async def health():

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception:
        return {"status": "unhealthy", "database": "disconnected"}


# @app.get("/webhook/whatsapp")
# async def verify_webhook(
#     hub_mode: str = Query(None, alias="hub.mode"),
#     hub_verify_token: str = Query(None, alias="hub.verify_token"),
#     hub_challenge: str = Query(None, alias="hub.challenge"),
# ):
#     """Meta sends a GET request to verify the webhook during setup."""
#     if hub_mode == "subscribe" and hub_verify_token == Config.WHATSAPP_VERIFY_TOKEN:
#         return int(hub_challenge)
#     raise HTTPException(status_code=403, detail="Verification failed")


# @app.post("/webhook/whatsapp")
# async def whatsapp_webhook(request: Request):
#     """Receives incoming WhatsApp messages via POST."""
#     data = await request.json()
#     print(data)
#     return {"status": "ok"}
