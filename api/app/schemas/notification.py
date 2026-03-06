from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    body: str
    target_type: str
    target_id: str
    is_read: bool
    created_at: datetime


class PaginatedNotificationResponse(BaseModel):
    items: list[NotificationResponse] = []
    total: int = 0


class UnreadCountResponse(BaseModel):
    count: int = 0
