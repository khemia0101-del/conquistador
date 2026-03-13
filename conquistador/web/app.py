"""FastAPI application — main entry point."""

from fastapi import FastAPI, WebSocket, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.models.base import get_db
from conquistador.chatbot.engine import chat_handler
from conquistador.web.routes import public, leads, contractor, partners, admin, reviews

app = FastAPI(
    title="Conquistador Oil, Heating & Air Conditioning",
    description="24/7 heating oil delivery and HVAC services in Central Pennsylvania",
    version="1.0.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include route modules
app.include_router(public.router)
app.include_router(leads.router)
app.include_router(contractor.router)
app.include_router(partners.router)
app.include_router(admin.router)
app.include_router(reviews.router)


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    await chat_handler(websocket, db)


@app.get("/health")
async def health():
    return {"status": "ok"}
