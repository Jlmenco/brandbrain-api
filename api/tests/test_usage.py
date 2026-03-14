"""Testes para Usage Logs, Overview de billing e Quota por plano."""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.usage import UsageLog
from app.services.usage_service import log_usage, check_quota, get_quota_status, PLAN_QUOTAS


# ---------- helpers ----------

def _seed_usage(session: Session, org_id: str, cc_id: str, user_id: str):
    """Insere registros de uso diretamente no banco para testes de overview."""
    logs = [
        UsageLog(
            org_id=org_id, cost_center_id=cc_id, user_id=user_id,
            resource_type="avatar", provider="dalle",
            units=1, unit_type="images", cost_usd=0.04,
            created_at=datetime.utcnow(),
        ),
        UsageLog(
            org_id=org_id, cost_center_id=cc_id, user_id=user_id,
            resource_type="tts", provider="elevenlabs",
            units=500, unit_type="chars", cost_usd=0.15,
            created_at=datetime.utcnow(),
        ),
        UsageLog(
            org_id=org_id, cost_center_id=cc_id, user_id=user_id,
            resource_type="video", provider="hedra",
            units=30, unit_type="video_seconds", cost_usd=3.0,
            created_at=datetime.utcnow(),
        ),
    ]
    for log in logs:
        session.add(log)
    session.commit()


# ---------- log_usage service ----------

def test_log_usage_service(session: Session, test_org, test_cc, test_user):
    log_usage(
        session,
        org_id=test_org.id,
        cost_center_id=test_cc.id,
        user_id=test_user.id,
        resource_type="avatar",
        provider="dalle",
        units=1,
        unit_type="images",
    )
    from sqlmodel import select
    logs = session.exec(select(UsageLog).where(UsageLog.org_id == test_org.id)).all()
    assert len(logs) == 1
    assert logs[0].resource_type == "avatar"
    assert logs[0].cost_usd == pytest.approx(0.04, abs=0.001)


def test_log_usage_unknown_provider(session: Session, test_org, test_cc, test_user):
    """Provider desconhecido deve registrar com custo 0."""
    log_usage(
        session,
        org_id=test_org.id,
        cost_center_id=test_cc.id,
        user_id=test_user.id,
        resource_type="custom",
        provider="unknown_provider",
        units=10,
        unit_type="requests",
    )
    from sqlmodel import select
    logs = session.exec(select(UsageLog).where(UsageLog.org_id == test_org.id)).all()
    assert len(logs) == 1
    assert logs[0].cost_usd == 0.0


# ---------- GET /usage/overview ----------

def test_usage_overview_empty(client: TestClient, test_org):
    resp = client.get("/usage/overview", params={"org_id": test_org.id, "days": 30})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cost_usd"] == 0.0
    assert data["by_resource"] == []


def test_usage_overview_with_data(client: TestClient, session: Session, test_org, test_cc, test_user):
    _seed_usage(session, test_org.id, test_cc.id, test_user.id)

    resp = client.get("/usage/overview", params={"org_id": test_org.id, "days": 30})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cost_usd"] == pytest.approx(3.19, abs=0.01)
    assert len(data["by_resource"]) == 3

    providers = {r["provider"] for r in data["by_resource"]}
    assert "dalle" in providers
    assert "elevenlabs" in providers
    assert "hedra" in providers


def test_usage_overview_period_filter(client: TestClient, session: Session, test_org, test_cc, test_user):
    """Registros com mais de 7 dias nao devem aparecer no overview de 7 dias."""
    old_log = UsageLog(
        org_id=test_org.id, cost_center_id=test_cc.id, user_id=test_user.id,
        resource_type="avatar", provider="dalle",
        units=1, unit_type="images", cost_usd=0.04,
        created_at=datetime.utcnow() - timedelta(days=10),
    )
    session.add(old_log)
    session.commit()

    resp = client.get("/usage/overview", params={"org_id": test_org.id, "days": 7})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cost_usd"] == 0.0


# ---------- GET /usage/logs ----------

def test_usage_logs_list(client: TestClient, session: Session, test_org, test_cc, test_user):
    _seed_usage(session, test_org.id, test_cc.id, test_user.id)

    resp = client.get("/usage/logs", params={"org_id": test_org.id})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 3


def test_usage_logs_pagination(client: TestClient, session: Session, test_org, test_cc, test_user):
    _seed_usage(session, test_org.id, test_cc.id, test_user.id)

    resp = client.get("/usage/logs", params={"org_id": test_org.id, "limit": 2, "skip": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2


# ---------- Quota por plano ----------

def test_check_quota_under_limit(session: Session, test_org):
    """Sem uso registrado, check_quota nao deve lancar excecao."""
    test_org.plan = "trial"
    session.add(test_org)
    session.commit()
    # Nao deve lancar HTTPException
    check_quota(session, test_org.id, "video")


def test_check_quota_at_limit_raises(session: Session, test_org, test_cc, test_user):
    """Ao atingir o limite, check_quota deve lancar 429."""
    from fastapi import HTTPException

    test_org.plan = "trial"
    session.add(test_org)
    session.commit()

    limit = PLAN_QUOTAS["trial"]["video"]  # 2
    for _ in range(limit):
        session.add(UsageLog(
            org_id=test_org.id, cost_center_id=test_cc.id, user_id=test_user.id,
            resource_type="video", provider="hedra",
            units=30, unit_type="seconds", cost_usd=0.3,
            created_at=datetime.utcnow(),
        ))
    session.commit()

    with pytest.raises(HTTPException) as exc_info:
        check_quota(session, test_org.id, "video")
    assert exc_info.value.status_code == 429
    assert "2" in exc_info.value.detail  # menciona o limite


def test_check_quota_unlimited_plan(session: Session, test_org, test_cc, test_user):
    """Plano group_monthly tem avatar ilimitado — nunca deve bloquear."""
    test_org.plan = "group_monthly"
    session.add(test_org)
    session.commit()

    # Inserir muitos avatares
    for _ in range(500):
        session.add(UsageLog(
            org_id=test_org.id, cost_center_id=test_cc.id, user_id=test_user.id,
            resource_type="avatar", provider="dalle",
            units=1, unit_type="images", cost_usd=0.04,
            created_at=datetime.utcnow(),
        ))
    session.commit()

    # Nao deve lancar
    check_quota(session, test_org.id, "avatar")


def test_get_quota_status_trial(session: Session, test_org, test_cc, test_user):
    """get_quota_status retorna used/limit corretos para plano trial."""
    test_org.plan = "trial"
    session.add(test_org)
    session.commit()

    session.add(UsageLog(
        org_id=test_org.id, cost_center_id=test_cc.id, user_id=test_user.id,
        resource_type="video", provider="hedra",
        units=30, unit_type="seconds", cost_usd=0.3,
        created_at=datetime.utcnow(),
    ))
    session.commit()

    status = get_quota_status(session, test_org.id)
    assert "video" in status
    assert status["video"]["used"] == 1
    assert status["video"]["limit"] == PLAN_QUOTAS["trial"]["video"]
    assert "avatar" in status
    assert status["avatar"]["used"] == 0


def test_get_quota_endpoint(client: TestClient, session: Session, test_org, test_cc, test_user):
    """GET /usage/quota deve retornar o status de quota da org."""
    test_org.plan = "solo_monthly"
    session.add(test_org)
    session.commit()

    resp = client.get("/usage/quota", params={"org_id": test_org.id})
    assert resp.status_code == 200
    data = resp.json()
    assert "video" in data
    assert "avatar" in data
    assert data["video"]["limit"] == PLAN_QUOTAS["solo_monthly"]["video"]
    assert data["video"]["used"] == 0


def test_quota_ignores_previous_month(session: Session, test_org, test_cc, test_user):
    """Logs do mes anterior nao devem contar na quota do mes corrente."""
    test_org.plan = "trial"
    session.add(test_org)
    session.commit()

    limit = PLAN_QUOTAS["trial"]["video"]
    # Inserir logs no mes passado
    last_month = datetime.utcnow().replace(day=1) - timedelta(days=1)
    for _ in range(limit + 5):
        session.add(UsageLog(
            org_id=test_org.id, cost_center_id=test_cc.id, user_id=test_user.id,
            resource_type="video", provider="hedra",
            units=30, unit_type="seconds", cost_usd=0.3,
            created_at=last_month,
        ))
    session.commit()

    # Mes corrente: sem uso -> nao deve bloquear
    check_quota(session, test_org.id, "video")
