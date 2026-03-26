"""FastAPI application — main entry point."""

from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.models.base import get_db
from conquistador.chatbot.engine import chat_handler
from conquistador.config import get_settings, BASE_DIR
from conquistador.web.routes import public, leads, contractor, partners, admin, reviews, webhooks

settings = get_settings()

app = FastAPI(
    title="Conquistador Oil, Heating & Air Conditioning",
    description="24/7 heating oil delivery and HVAC services in Central Pennsylvania",
    version="1.0.0",
)

# CORS — allow the Manus-hosted site to call our API and embed the chatbot
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Include route modules
app.include_router(public.router)
app.include_router(leads.router)
app.include_router(contractor.router)
app.include_router(partners.router)
app.include_router(admin.router)
app.include_router(reviews.router)
app.include_router(webhooks.router)


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    await chat_handler(websocket, db)


@app.get("/health")
async def health():
    return {"status": "ok"}
