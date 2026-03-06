from pydantic import BaseModel
from typing import Optional

class SocialAccountResponse(BaseModel):
    id: str
    org_id: str
    cost_center_id: str
    provider: str
    account_name: str
    status: str
