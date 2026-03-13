import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = "Live News Aggregator"
    database_url: str = f"sqlite:///{BASE_DIR / 'news.db'}"
    fetch_interval_minutes: int = int(os.getenv("FETCH_INTERVAL_MINUTES", "15"))
    rss_feeds: tuple[str, ...] = tuple(
        feed.strip()
        for feed in os.getenv(
            "RSS_FEEDS",
            "https://feeds.bbci.co.uk/news/rss.xml,https://feeds.reuters.com/reuters/topNews",
        ).split(",")
        if feed.strip()
    )
    news_api_key: str | None = os.getenv("NEWS_API_KEY")
    news_api_endpoint: str = os.getenv(
        "NEWS_API_ENDPOINT", "https://newsapi.org/v2/top-headlines"
    )


settings = Settings()
