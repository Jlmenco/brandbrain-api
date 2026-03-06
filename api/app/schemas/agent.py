from pydantic import BaseModel
from typing import Optional

class AgentRunRequest(BaseModel):
    org_id: str
    cc_id: Optional[str] = None
    influencer_id: Optional[str] = None
    intent: str  # create_influencer | plan_week | generate_drafts | adapt_from_master
    message: str = ""
    channels: list[str] = []
    objectives: list[str] = []

class AgentRunResponse(BaseModel):
    session_id: str
    plan: str
    proposed_actions: list[dict]
    outputs: list[dict]
    next_steps: list[str]
