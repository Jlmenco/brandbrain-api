import logging
from datetime import datetime

from sqlmodel import Session, select

from app.models.onboarding import OnboardingProgress, ONBOARDING_STEPS

logger = logging.getLogger(__name__)


def get_or_create_progress(db: Session, user_id: str, org_id: str) -> OnboardingProgress:
    """Retorna progresso existente ou cria um novo."""
    progress = db.exec(
        select(OnboardingProgress).where(
            OnboardingProgress.user_id == user_id,
            OnboardingProgress.org_id == org_id,
        )
    ).first()

    if progress:
        return progress

    progress = OnboardingProgress(user_id=user_id, org_id=org_id)
    db.add(progress)
    db.commit()
    db.refresh(progress)
    return progress


def complete_step(db: Session, user_id: str, org_id: str, step: str) -> OnboardingProgress:
    """Marca um step como completo. Ignora steps invalidos ou ja completados."""
    if step not in ONBOARDING_STEPS:
        logger.warning("Invalid onboarding step: %s", step)
        return get_or_create_progress(db, user_id, org_id)

    progress = get_or_create_progress(db, user_id, org_id)

    if step in progress.steps_completed:
        return progress

    # SQLModel JSON columns need reassignment for change detection
    completed = list(progress.steps_completed)
    completed.append(step)
    progress.steps_completed = completed
    progress.updated_at = datetime.utcnow()
    db.add(progress)
    db.commit()
    db.refresh(progress)
    logger.info("Onboarding step '%s' completed for user=%s org=%s", step, user_id, org_id)
    return progress


def is_onboarding_complete(db: Session, user_id: str, org_id: str) -> bool:
    """Verifica se todos os steps foram completados ou dismissed."""
    progress = get_or_create_progress(db, user_id, org_id)
    if progress.is_dismissed:
        return True
    return all(s in progress.steps_completed for s in ONBOARDING_STEPS)
