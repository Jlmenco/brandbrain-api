"""Base para providers de publicacao."""
import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger("worker.providers")

# Timeout padrao para chamadas HTTP a APIs sociais
HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


@dataclass
class PublishResult:
    success: bool
    provider_post_id: str = ""
    provider_post_url: str = ""
    error: str = ""
