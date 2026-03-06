from pydantic import BaseModel
from typing import Optional

class OrgCreate(BaseModel):
    name: str

class OrgResponse(BaseModel):
    id: str
    name: str
    role: str | None = None

class OrgMemberCreate(BaseModel):
    user_id: str
    role: str = "viewer"  # owner | admin | editor | viewer

class OrgMemberResponse(BaseModel):
    id: str
    org_id: str
    user_id: str
    role: str
