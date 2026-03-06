import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


class AgentSession(SQLModel, table=True):
    __tablename__ = "agent_sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    cost_center_id: Optional[str] = Field(default=None, foreign_key="cost_centers.id")
    user_id: str = Field(foreign_key="users.id")
    agent_type: str = ""  # marketing | market
    status: str = Field(default="active")  # active | closed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AgentMessage(SQLModel, table=True):
    __tablename__ = "agent_messages"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="agent_sessions.id", index=True)
    role: str = ""  # user | agent | tool
    content: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentAction(SQLModel, table=True):
    __tablename__ = "agent_actions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="agent_sessions.id", index=True)
    action_type: str = ""  # create_influencer, generate_drafts, etc.
    status: str = Field(default="proposed")  # proposed | executed | failed
    metadata_json: dict = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    created_at: datetime = Field(default_factory=datetime.utcnow)
