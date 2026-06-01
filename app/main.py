from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .core import Config
from .core.exceptions import register_exception_handlers
from .api.router import api_router
from .api.endpoints.websocket_endpoints import ws_router

app = FastAPI()

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
def health():
    return {"status": "healthy"}


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
