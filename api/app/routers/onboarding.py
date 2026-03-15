from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user
from app.models.onboarding import ONBOARDING_STEPS
from app.services.onboarding_service import get_or_create_progress, complete_step

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class OnboardingProgressResponse(BaseModel):
    id: str
    user_id: str
    org_id: str
    steps_completed: list[str]
    steps_total: list[str]
    is_dismissed: bool
    is_complete: bool


class CompleteStepRequest(BaseModel):
    step: str
    org_id: str


class DismissRequest(BaseModel):
    org_id: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _progress_response(progress) -> OnboardingProgressResponse:
    return OnboardingProgressResponse(
        id=progress.id,
        user_id=progress.user_id,
        org_id=progress.org_id,
        steps_completed=progress.steps_completed or [],
        steps_total=ONBOARDING_STEPS,
        is_dismissed=progress.is_dismissed,
        is_complete=progress.is_dismissed or all(
            s in (progress.steps_completed or []) for s in ONBOARDING_STEPS
        ),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/progress", response_model=OnboardingProgressResponse)
def get_progress(
    org_id: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Retorna progresso de onboarding do usuario na org."""
    progress = get_or_create_progress(db, current_user.id, org_id)
    return _progress_response(progress)


@router.post("/progress/complete-step", response_model=OnboardingProgressResponse)
def complete_step_endpoint(
    body: CompleteStepRequest,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Marca um step como completo."""
    if body.step not in ONBOARDING_STEPS:
        raise HTTPException(status_code=400, detail=f"Step invalido. Validos: {ONBOARDING_STEPS}")
    progress = complete_step(db, current_user.id, body.org_id, body.step)
    return _progress_response(progress)


@router.post("/progress/dismiss", response_model=OnboardingProgressResponse)
def dismiss_onboarding(
    body: DismissRequest,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Esconde o checklist permanentemente."""
    progress = get_or_create_progress(db, current_user.id, body.org_id)
    progress.is_dismissed = True
    progress.updated_at = datetime.utcnow()
    db.add(progress)
    db.commit()
    db.refresh(progress)
    return _progress_response(progress)
