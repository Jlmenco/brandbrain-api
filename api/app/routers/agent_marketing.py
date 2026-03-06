from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.schemas.agent import AgentRunRequest, AgentRunResponse
from app.dependencies import get_current_user
from app.agents.marketing_agent import run_marketing_agent

router = APIRouter()


@router.post("/run", response_model=AgentRunResponse)
def run_agent(body: AgentRunRequest, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    return run_marketing_agent(db, current_user, body)
