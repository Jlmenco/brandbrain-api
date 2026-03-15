"""Testes para drip campaigns (router + service)."""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.drip import DripCampaign, DripStep, DripEnrollment
from app.models.organization import Organization
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_campaign(session: Session, org_id: str = "org-1", trigger: str = "welcome") -> DripCampaign:
    campaign = DripCampaign(
        id="camp-1",
        org_id=org_id,
        name="Welcome Campaign",
        trigger_event=trigger,
    )
    session.add(campaign)
    step1 = DripStep(
        campaign_id=campaign.id,
        step_order=0,
        delay_hours=0,
        subject="Bem-vindo, {name}!",
        body_template="<p>Ola, {name}! Bem-vindo ao {org_name}.</p>",
    )
    step2 = DripStep(
        campaign_id=campaign.id,
        step_order=1,
        delay_hours=72,
        subject="Dicas para {name}",
        body_template="<p>Aqui vao algumas dicas para comecar.</p>",
    )
    session.add(step1)
    session.add(step2)
    session.commit()
    session.refresh(campaign)
    return campaign


# ---------------------------------------------------------------------------
# GET /drip-campaigns
# ---------------------------------------------------------------------------

def test_list_campaigns_empty(client: TestClient, test_org):
    resp = client.get("/drip-campaigns", params={"org_id": test_org.id})
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_campaigns(client: TestClient, session: Session, test_org):
    _create_campaign(session, test_org.id)
    resp = client.get("/drip-campaigns", params={"org_id": test_org.id})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Welcome Campaign"
    assert len(data[0]["steps"]) == 2


def test_list_campaigns_requires_org_id(client: TestClient, test_org):
    resp = client.get("/drip-campaigns")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /drip-campaigns
# ---------------------------------------------------------------------------

def test_create_campaign(client: TestClient, test_org):
    payload = {
        "name": "Trial Expiring",
        "trigger_event": "trial_expiring",
        "org_id": test_org.id,
        "steps": [
            {"step_order": 0, "delay_hours": 0, "subject": "Seu trial", "body_template": "<p>Aviso</p>"},
        ],
    }
    resp = client.post("/drip-campaigns", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Trial Expiring"
    assert data["trigger_event"] == "trial_expiring"
    assert data["is_active"] is True
    assert len(data["steps"]) == 1


def test_create_campaign_no_steps(client: TestClient, test_org):
    payload = {
        "name": "Empty Campaign",
        "trigger_event": "custom",
        "org_id": test_org.id,
        "steps": [],
    }
    resp = client.post("/drip-campaigns", json=payload)
    assert resp.status_code == 200
    assert len(resp.json()["steps"]) == 0


# ---------------------------------------------------------------------------
# PATCH /drip-campaigns/{id}
# ---------------------------------------------------------------------------

def test_update_campaign_name(client: TestClient, session: Session, test_org):
    campaign = _create_campaign(session, test_org.id)
    resp = client.patch(f"/drip-campaigns/{campaign.id}", json={"name": "Renamed"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"


def test_toggle_campaign_active(client: TestClient, session: Session, test_org):
    campaign = _create_campaign(session, test_org.id)
    resp = client.patch(f"/drip-campaigns/{campaign.id}", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_update_campaign_steps(client: TestClient, session: Session, test_org):
    campaign = _create_campaign(session, test_org.id)
    new_steps = [
        {"step_order": 0, "delay_hours": 0, "subject": "New Step", "body_template": "<p>New</p>"},
    ]
    resp = client.patch(f"/drip-campaigns/{campaign.id}", json={"steps": new_steps})
    assert resp.status_code == 200
    assert len(resp.json()["steps"]) == 1
    assert resp.json()["steps"][0]["subject"] == "New Step"


def test_update_campaign_not_found(client: TestClient, test_org):
    resp = client.patch("/drip-campaigns/nonexistent", json={"name": "X"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /drip-campaigns/{id}
# ---------------------------------------------------------------------------

def test_deactivate_campaign(client: TestClient, session: Session, test_org):
    campaign = _create_campaign(session, test_org.id)
    resp = client.delete(f"/drip-campaigns/{campaign.id}")
    assert resp.status_code == 200
    session.refresh(campaign)
    assert campaign.is_active is False


# ---------------------------------------------------------------------------
# Enrollments
# ---------------------------------------------------------------------------

def test_list_enrollments_empty(client: TestClient, session: Session, test_org):
    campaign = _create_campaign(session, test_org.id)
    resp = client.get(f"/drip-campaigns/{campaign.id}/enrollments")
    assert resp.status_code == 200
    assert resp.json() == []


def test_cancel_enrollment(client: TestClient, session: Session, test_org, test_user):
    campaign = _create_campaign(session, test_org.id)
    enrollment = DripEnrollment(
        id="enr-1",
        campaign_id=campaign.id,
        user_id=test_user.id,
        org_id=test_org.id,
        next_send_at=datetime.utcnow(),
    )
    session.add(enrollment)
    session.commit()

    resp = client.post(f"/drip-campaigns/{campaign.id}/enrollments/enr-1/cancel")
    assert resp.status_code == 200
    session.refresh(enrollment)
    assert enrollment.status == "cancelled"


# ---------------------------------------------------------------------------
# Service: auto_enroll_on_event
# ---------------------------------------------------------------------------

def test_auto_enroll_on_event(session: Session, test_org, test_user):
    from app.services.drip_service import auto_enroll_on_event
    _create_campaign(session, test_org.id, "welcome")
    count = auto_enroll_on_event(session, "welcome", test_user.id, test_org.id)
    assert count == 1

    # Second call should not duplicate
    count2 = auto_enroll_on_event(session, "welcome", test_user.id, test_org.id)
    assert count2 == 0


def test_auto_enroll_no_matching_campaign(session: Session, test_org, test_user):
    from app.services.drip_service import auto_enroll_on_event
    _create_campaign(session, test_org.id, "trial_expiring")
    count = auto_enroll_on_event(session, "welcome", test_user.id, test_org.id)
    assert count == 0


# ---------------------------------------------------------------------------
# Service: process_pending_drips
# ---------------------------------------------------------------------------

def test_process_pending_drips(session: Session, test_org, test_user):
    from app.services.drip_service import process_pending_drips
    campaign = _create_campaign(session, test_org.id)
    enrollment = DripEnrollment(
        campaign_id=campaign.id,
        user_id=test_user.id,
        org_id=test_org.id,
        current_step=0,
        next_send_at=datetime.utcnow() - timedelta(minutes=1),
    )
    session.add(enrollment)
    session.commit()

    processed = process_pending_drips(session)
    assert processed == 1

    session.refresh(enrollment)
    assert enrollment.current_step == 1
    assert enrollment.status == "active"  # Still has step 1 to go


def test_process_completes_enrollment(session: Session, test_org, test_user):
    from app.services.drip_service import process_pending_drips
    campaign = _create_campaign(session, test_org.id)
    # Start at step 1 (last step)
    enrollment = DripEnrollment(
        campaign_id=campaign.id,
        user_id=test_user.id,
        org_id=test_org.id,
        current_step=1,
        next_send_at=datetime.utcnow() - timedelta(minutes=1),
    )
    session.add(enrollment)
    session.commit()

    processed = process_pending_drips(session)
    assert processed == 1

    session.refresh(enrollment)
    assert enrollment.status == "completed"
    assert enrollment.completed_at is not None
    assert enrollment.next_send_at is None
