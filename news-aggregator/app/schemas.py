from datetime import datetime

from pydantic import BaseModel


class ArticleOut(BaseModel):
    id: int
    title: str
    url: str
    source: str
    published_at: datetime
    summary: str | None = None
    image_url: str | None = None

    model_config = {"from_attributes": True}
