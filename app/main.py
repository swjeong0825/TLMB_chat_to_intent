import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.api.routers.chat_router import router as chat_router
from app.dependencies import get_chat_handler
from app.rate_limit import limiter, register_rate_limit_middleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Eagerly build and validate the full pipeline at startup so a
    # misconfigured API key or unknown LLM_PROVIDER fails fast.
    get_chat_handler()
    yield


app = FastAPI(
    title="Tennis League Chatbot — Chat-to-Intent Server",
    description=(
        "Receives natural-language chat messages, classifies them into a structured intent "
        "using an LLM, and returns either fetched league data (Read intents) or a pre-filled "
        "form payload (Write intents) for the frontend to render and submit.\n\n"
        "Set **LLM_PROVIDER** in `.env` to switch providers: "
        "`groq` (default) | `openai` | `google`."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

ALLOWED_ORIGINS = [
    "https://tlmb.swjapps.com",
    "https://www.tlmb.swjapps.com",
    # "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_rate_limit_middleware(app)

app.include_router(chat_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
