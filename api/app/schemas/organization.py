from datetime import datetime
from pydantic import BaseModel
from typing import Literal, Optional

AccountType = Literal["solo", "agency", "group"]
PlanType = Literal["trial", "solo_monthly", "agency_monthly", "group_monthly", "active"]


class OrgCreate(BaseModel):
    name: str
    account_type: AccountType = "agency"


class OrgResponse(BaseModel):
    id: str
    name: str
    role: str | None = None
    billing_alert_threshold: Optional[float] = None
    account_type: str = "agency"
    parent_org_id: Optional[str] = None
    plan: str = "active"
    trial_ends_at: Optional[datetime] = None


class OrgUpdate(BaseModel):
    name: Optional[str] = None
    billing_alert_threshold: Optional[float] = None
    account_type: Optional[AccountType] = None


class OrgMemberCreate(BaseModel):
    user_id: str
    role: str = "viewer"  # owner | admin | editor | viewer


class OrgMemberResponse(BaseModel):
    id: str
    org_id: str
    user_id: str
    role: str


class SoloSetupRequest(BaseModel):
    brand_name: str
    niche: str


class OrgUpgradeRequest(BaseModel):
    target_type: AccountType = "agency"


class OrgActivateRequest(BaseModel):
    plan: PlanType
