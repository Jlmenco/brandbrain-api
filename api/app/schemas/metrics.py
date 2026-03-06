from pydantic import BaseModel
from datetime import date
from typing import Optional

class MetricsDailyResponse(BaseModel):
    id: str
    content_item_id: str
    date: date
    impressions: int
    likes: int
    comments: int
    shares: int
    clicks: int
    followers_delta: int

class MetricsOverview(BaseModel):
    total_impressions: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    total_clicks: int = 0
    total_followers_delta: int = 0
    total_posts: int = 0
