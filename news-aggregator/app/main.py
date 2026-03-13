from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from contextlib import suppress
from pathlib import Path

from fastapi import Depends, FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, init_db
from app.ingestion import ingest_once, run_ingestion_loop
from app.models import Article
from app.schemas import ArticleOut
from app.ws_manager import ConnectionManager


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

ws_manager = ConnectionManager()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    # Warm cache immediately at boot so first page load has data.
    try:
        fresh_articles = await ingest_once(SessionLocal)
        if fresh_articles:
            await broadcast_new_articles(fresh_articles)
    except Exception as exc:
        logger.exception("Initial ingestion failed: %s", exc)

    ingestion_task = asyncio.create_task(run_ingestion_loop(SessionLocal, broadcast_new_articles))
    app.state.ingestion_task = ingestion_task

    yield

    ingestion_task.cancel()
    with suppress(asyncio.CancelledError):
        await ingestion_task


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/news", response_model=list[ArticleOut])
def get_news(
    source: str | None = Query(default=None, description="Filter by source name"),
    db: Session = Depends(get_db),
) -> list[Article]:
    stmt = select(Article)
    if source:
        stmt = stmt.where(Article.source == source)
    stmt = stmt.order_by(desc(Article.published_at)).limit(50)

    return list(db.execute(stmt).scalars().all())


@app.websocket("/ws/news")
async def websocket_news(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep the socket open for server push; disconnect is handled by exception.
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        await ws_manager.disconnect(websocket)


async def broadcast_new_articles(articles: list[Article]) -> None:
    for article in articles:
        payload = ArticleOut.model_validate(article).model_dump(mode="json")
        await ws_manager.broadcast_json(payload)
