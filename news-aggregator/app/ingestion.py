from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Article


logger = logging.getLogger(__name__)


@dataclass
class IngestedArticle:
    title: str
    url: str
    source: str
    published_at: datetime
    summary: str | None
    image_url: str | None


async def fetch_rss_articles(client: httpx.AsyncClient) -> list[IngestedArticle]:
    all_articles: list[IngestedArticle] = []

    for feed_url in settings.rss_feeds:
        try:
            response = await client.get(feed_url, timeout=20)
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
            feed_title = parsed.feed.get("title", "RSS Feed")

            for entry in parsed.entries[:30]:
                url = entry.get("link")
                if not url:
                    continue

                all_articles.append(
                    IngestedArticle(
                        title=(entry.get("title") or "Untitled").strip(),
                        url=url.strip(),
                        source=feed_title,
                        published_at=_parse_date(entry),
                        summary=(entry.get("summary") or entry.get("description") or "").strip() or None,
                        image_url=_extract_feed_image(entry),
                    )
                )
        except Exception as exc:
            logger.exception("Failed to fetch RSS feed %s: %s", feed_url, exc)

    return all_articles


async def fetch_newsapi_articles(client: httpx.AsyncClient) -> list[IngestedArticle]:
    if not settings.news_api_key:
        return []

    params = {
        "apiKey": settings.news_api_key,
        "language": "en",
        "pageSize": 20,
    }

    try:
        response = await client.get(settings.news_api_endpoint, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        logger.exception("Failed to fetch NewsAPI articles: %s", exc)
        return []

    records = payload.get("articles", [])
    articles: list[IngestedArticle] = []

    for record in records:
        url = (record.get("url") or "").strip()
        title = (record.get("title") or "").strip()
        if not url or not title:
            continue

        source_info = record.get("source") or {}
        source_name = (source_info.get("name") or "NewsAPI").strip()

        published_at = _parse_iso_datetime(record.get("publishedAt"))
        summary = (record.get("description") or record.get("content") or "").strip() or None
        image_url = (record.get("urlToImage") or "").strip() or None

        articles.append(
            IngestedArticle(
                title=title,
                url=url,
                source=source_name,
                published_at=published_at,
                summary=summary,
                image_url=image_url,
            )
        )

    return articles


async def ingest_once(
    session_factory: sessionmaker[Session],
) -> list[Article]:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        rss_task = asyncio.create_task(fetch_rss_articles(client))
        rest_task = asyncio.create_task(fetch_newsapi_articles(client))
        rss_articles, rest_articles = await asyncio.gather(rss_task, rest_task)

    candidate_articles = rss_articles + rest_articles
    if not candidate_articles:
        return []

    new_articles: list[Article] = []
    with session_factory() as session:
        for item in candidate_articles:
            if _article_exists(session, item.url):
                continue

            entity = Article(
                title=item.title,
                url=item.url,
                source=item.source,
                published_at=item.published_at,
                summary=item.summary,
                image_url=item.image_url,
            )
            session.add(entity)
            try:
                session.commit()
                session.refresh(entity)
                new_articles.append(entity)
            except IntegrityError:
                session.rollback()
            except Exception as exc:
                session.rollback()
                logger.exception("Failed to save article %s: %s", item.url, exc)

    new_articles.sort(key=lambda a: a.published_at, reverse=True)
    return new_articles


async def run_ingestion_loop(session_factory: sessionmaker[Session], on_new_articles) -> None:
    interval_seconds = max(settings.fetch_interval_minutes, 1) * 60

    while True:
        try:
            new_articles = await ingest_once(session_factory)
            if new_articles:
                await on_new_articles(new_articles)
                logger.info("Ingested %s new article(s)", len(new_articles))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Ingestion loop failed: %s", exc)

        await asyncio.sleep(interval_seconds)


def _article_exists(session: Session, url: str) -> bool:
    stmt = select(Article.id).where(Article.url == url)
    return session.execute(stmt).scalar_one_or_none() is not None


def _parse_iso_datetime(raw_date: Any) -> datetime:
    if not raw_date or not isinstance(raw_date, str):
        return datetime.now(UTC)

    candidate = raw_date.replace("Z", "+00:00")
    try:
        value = datetime.fromisoformat(candidate)
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    except ValueError:
        return datetime.now(UTC)


def _parse_date(entry: dict[str, Any]) -> datetime:
    # RSS feeds vary wildly in date keys and format.
    for key in ("published", "updated", "pubDate"):
        raw = entry.get(key)
        if not raw:
            continue
        try:
            parsed = parsedate_to_datetime(str(raw))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except Exception:
            continue

    struct_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if struct_time:
        return datetime(*struct_time[:6], tzinfo=UTC)

    return datetime.now(UTC)


def _extract_feed_image(entry: dict[str, Any]) -> str | None:
    media_content = entry.get("media_content") or []
    if media_content and isinstance(media_content, list):
        first = media_content[0] or {}
        if isinstance(first, dict) and first.get("url"):
            return str(first["url"]).strip()

    media_thumbnail = entry.get("media_thumbnail") or []
    if media_thumbnail and isinstance(media_thumbnail, list):
        first = media_thumbnail[0] or {}
        if isinstance(first, dict) and first.get("url"):
            return str(first["url"]).strip()

    links = entry.get("links") or []
    for link in links:
        if isinstance(link, dict) and str(link.get("type", "")).startswith("image"):
            href = link.get("href")
            if href:
                return str(href).strip()

    return None
