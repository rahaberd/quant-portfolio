# Live News Aggregator

A production-style FastAPI + SQLite application that ingests live news from RSS and REST sources, caches them locally, and streams new articles to the browser via WebSockets.

## Features

- Async ingestion engine with two source types:
  - RSS feeds (BBC + Reuters by default)
  - REST API (NewsAPI-style endpoint using API key from `.env`)
- Automatic background refresh every 15 minutes (configurable)
- SQLite cache with URL-based deduplication
- `GET /api/news` endpoint with source filtering
- `WS /ws/news` endpoint for live, push-based updates
- Zero-build frontend using Tailwind CDN + Vanilla JS

## Project Structure

```text
news-aggregator/
  app/
    __init__.py
    config.py
    database.py
    ingestion.py
    main.py
    models.py
    schemas.py
    ws_manager.py
  static/
    app.js
    index.html
  .env.example
  .gitignore
  README.md
  requirements.txt
```

## Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables:

```bash
copy .env.example .env
```

Set `NEWS_API_KEY` in `.env` if you want REST source ingestion.

## Run

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 in your browser.

## API

- `GET /api/news`
  - Query params:
    - `source` (optional): exact source name filter
  - Returns: latest 50 articles by publication date descending.

- `WS /ws/news`
  - Pushes JSON payloads for newly ingested articles.

## Data Flow

1. On startup, the app initializes SQLite and runs an immediate ingestion pass.
2. The ingestion loop fetches RSS + REST data every configured interval.
3. New articles are normalized and inserted into SQLite if URL is not already present.
4. Newly saved articles are broadcast over WebSockets to connected clients.
5. Frontend fetches initial 50 records from `/api/news` and prepends incoming live updates from `WS /ws/news`.

## Notes

- If one upstream source fails, ingestion continues with remaining sources.
- If `NEWS_API_KEY` is empty, REST ingestion is skipped automatically.
