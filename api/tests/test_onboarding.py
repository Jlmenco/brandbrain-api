"""Testes para onboarding guiado (router + service)."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.onboarding import OnboardingProgress, ONBOARDING_STEPS
from app.models.organization import Organization
from app.models.user import User


# ---------------------------------------------------------------------------
# GET /onboarding/progress
# ---------------------------------------------------------------------------

def test_get_progress_creates_on_first_call(client: TestClient, test_org):
    resp = client.get("/onboarding/progress", params={"org_id": test_org.id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["org_id"] == test_org.id
    assert data["steps_completed"] == []
    assert data["steps_total"] == ONBOARDING_STEPS
    assert data["is_dismissed"] is False
    assert data["is_complete"] is False


def test_get_progress_returns_existing(client: TestClient, session: Session, test_org, test_user):
    progress = OnboardingProgress(
        user_id=test_user.id,
        org_id=test_org.id,
        steps_completed=["profile_setup", "first_influencer"],
    )
    session.add(progress)
    session.commit()

    resp = client.get("/onboarding/progress", params={"org_id": test_org.id})
    assert resp.status_code == 200
    data = resp.json()
    assert "profile_setup" in data["steps_completed"]
    assert "first_influencer" in data["steps_completed"]
    assert data["is_complete"] is False


# ---------------------------------------------------------------------------
# POST /onboarding/progress/complete-step
# ---------------------------------------------------------------------------

def test_complete_step(client: TestClient, test_org):
    resp = client.post(
        "/onboarding/progress/complete-step",
        json={"org_id": test_org.id, "step": "first_influencer"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "first_influencer" in data["steps_completed"]


def test_complete_step_idempotent(client: TestClient, test_org):
    client.post(
        "/onboarding/progress/complete-step",
        json={"org_id": test_org.id, "step": "first_influencer"},
    )
    resp = client.post(
        "/onboarding/progress/complete-step",
        json={"org_id": test_org.id, "step": "first_influencer"},
    )
    assert resp.status_code == 200
    assert resp.json()["steps_completed"].count("first_influencer") == 1


def test_complete_step_invalid(client: TestClient, test_org):
    resp = client.post(
        "/onboarding/progress/complete-step",
        json={"org_id": test_org.id, "step": "invalid_step"},
    )
    assert resp.status_code == 400


def test_complete_all_steps_marks_complete(client: TestClient, test_org):
    for step in ONBOARDING_STEPS:
        client.post(
            "/onboarding/progress/complete-step",
            json={"org_id": test_org.id, "step": step},
        )
    resp = client.get("/onboarding/progress", params={"org_id": test_org.id})
    assert resp.status_code == 200
    assert resp.json()["is_complete"] is True


# ---------------------------------------------------------------------------
# POST /onboarding/progress/dismiss
# ---------------------------------------------------------------------------

def test_dismiss_onboarding(client: TestClient, test_org):
    resp = client.post(
        "/onboarding/progress/dismiss",
        json={"org_id": test_org.id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_dismissed"] is True
    assert data["is_complete"] is True  # dismissed counts as complete


# ---------------------------------------------------------------------------
# Service: complete_step
# ---------------------------------------------------------------------------

def test_service_complete_step(session: Session, test_org, test_user):
    from app.services.onboarding_service import complete_step, get_or_create_progress

    progress = complete_step(session, test_user.id, test_org.id, "brand_kit")
    assert "brand_kit" in progress.steps_completed

    # Idempotent
    progress2 = complete_step(session, test_user.id, test_org.id, "brand_kit")
    assert progress2.steps_completed.count("brand_kit") == 1


def test_service_is_onboarding_complete(session: Session, test_org, test_user):
    from app.services.onboarding_service import complete_step, is_onboarding_complete

    assert is_onboarding_complete(session, test_user.id, test_org.id) is False

    for step in ONBOARDING_STEPS:
        complete_step(session, test_user.id, test_org.id, step)

    assert is_onboarding_complete(session, test_user.id, test_org.id) is True


def test_service_dismissed_counts_as_complete(session: Session, test_org, test_user):
    from app.services.onboarding_service import get_or_create_progress, is_onboarding_complete

    progress = get_or_create_progress(session, test_user.id, test_org.id)
    progress.is_dismissed = True
    session.add(progress)
    session.commit()

    assert is_onboarding_complete(session, test_user.id, test_org.id) is True
