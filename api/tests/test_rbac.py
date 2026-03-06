"""Testes de RBAC: verifica permissoes por role nos endpoints protegidos."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlmodel import Session

from app.main import app
from app.models.user import User
from app.models.organization import Organization
from app.models.cost_center import CostCenter
from app.models.influencer import Influencer
from app.models.content import ContentItem
from tests.conftest import make_client_for_user


@pytest.fixture(autouse=True)
def _cleanup_overrides():
    yield
    app.dependency_overrides.clear()


# ==========================================
# Editor: Content Permissions
# ==========================================


class TestEditorContentPermissions:
    """Editor pode criar/editar/submeter, mas NAO pode aprovar/rejeitar/publicar."""

    def test_editor_can_create_content(
        self, session: Session, editor_user: User, test_cc: CostCenter, test_influencer: Influencer
    ):
        client = make_client_for_user(session, editor_user)
        resp = client.post("/content-items", json={
            "cost_center_id": test_cc.id,
            "influencer_id": test_influencer.id,
            "provider_target": "instagram",
            "text": "Post do editor",
        })
        assert resp.status_code == 200

    def test_editor_can_update_content(
        self, session: Session, editor_user: User, test_content_item: ContentItem
    ):
        client = make_client_for_user(session, editor_user)
        resp = client.patch(f"/content-items/{test_content_item.id}", json={"text": "Editado"})
        assert resp.status_code == 200

    def test_editor_can_submit_review(
        self, session: Session, editor_user: User, test_content_item: ContentItem
    ):
        client = make_client_for_user(session, editor_user)
        resp = client.post(f"/content-items/{test_content_item.id}/submit-review")
        assert resp.status_code == 200

    def test_editor_cannot_approve(
        self, session: Session, editor_user: User, test_content_item: ContentItem
    ):
        test_content_item.status = "review"
        session.add(test_content_item)
        session.commit()
        client = make_client_for_user(session, editor_user)
        resp = client.post(f"/content-items/{test_content_item.id}/approve")
        assert resp.status_code == 403

    def test_editor_cannot_reject(
        self, session: Session, editor_user: User, test_content_item: ContentItem
    ):
        test_content_item.status = "review"
        session.add(test_content_item)
        session.commit()
        client = make_client_for_user(session, editor_user)
        resp = client.post(f"/content-items/{test_content_item.id}/reject")
        assert resp.status_code == 403

    def test_editor_cannot_request_changes(
        self, session: Session, editor_user: User, test_content_item: ContentItem
    ):
        test_content_item.status = "review"
        session.add(test_content_item)
        session.commit()
        client = make_client_for_user(session, editor_user)
        resp = client.post(f"/content-items/{test_content_item.id}/request-changes")
        assert resp.status_code == 403

    def test_editor_cannot_schedule(
        self, session: Session, editor_user: User, test_content_item: ContentItem
    ):
        test_content_item.status = "approved"
        session.add(test_content_item)
        session.commit()
        client = make_client_for_user(session, editor_user)
        scheduled_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        resp = client.post(
            f"/content-items/{test_content_item.id}/schedule",
            json={"scheduled_at": scheduled_time},
        )
        assert resp.status_code == 403

    @patch("app.routers.content_items._signal_worker")
    def test_editor_cannot_publish_now(
        self, mock_signal, session: Session, editor_user: User, test_content_item: ContentItem
    ):
        test_content_item.status = "approved"
        session.add(test_content_item)
        session.commit()
        client = make_client_for_user(session, editor_user)
        resp = client.post(f"/content-items/{test_content_item.id}/publish-now")
        assert resp.status_code == 403


# ==========================================
# Viewer: Content Permissions
# ==========================================


class TestViewerContentPermissions:
    """Viewer pode listar/ver, mas NAO pode criar/editar/submeter."""

    def test_viewer_can_list_content(
        self, session: Session, viewer_user: User, test_content_item: ContentItem
    ):
        client = make_client_for_user(session, viewer_user)
        resp = client.get("/content-items")
        assert resp.status_code == 200

    def test_viewer_can_get_content(
        self, session: Session, viewer_user: User, test_content_item: ContentItem
    ):
        client = make_client_for_user(session, viewer_user)
        resp = client.get(f"/content-items/{test_content_item.id}")
        assert resp.status_code == 200

    def test_viewer_cannot_create_content(
        self, session: Session, viewer_user: User, test_cc: CostCenter, test_influencer: Influencer
    ):
        client = make_client_for_user(session, viewer_user)
        resp = client.post("/content-items", json={
            "cost_center_id": test_cc.id,
            "influencer_id": test_influencer.id,
            "provider_target": "instagram",
            "text": "Tentativa do viewer",
        })
        assert resp.status_code == 403

    def test_viewer_cannot_update_content(
        self, session: Session, viewer_user: User, test_content_item: ContentItem
    ):
        client = make_client_for_user(session, viewer_user)
        resp = client.patch(f"/content-items/{test_content_item.id}", json={"text": "Tentativa"})
        assert resp.status_code == 403

    def test_viewer_cannot_approve(
        self, session: Session, viewer_user: User, test_content_item: ContentItem
    ):
        test_content_item.status = "review"
        session.add(test_content_item)
        session.commit()
        client = make_client_for_user(session, viewer_user)
        resp = client.post(f"/content-items/{test_content_item.id}/approve")
        assert resp.status_code == 403


# ==========================================
# Influencers: Permission Boundaries
# ==========================================


class TestInfluencerPermissions:
    """create/update/brand-kit requerem ADMIN_ROLES."""

    def test_viewer_cannot_create_influencer(
        self, session: Session, viewer_user: User, test_org: Organization
    ):
        client = make_client_for_user(session, viewer_user)
        resp = client.post(
            f"/influencers?org_id={test_org.id}",
            json={
                "name": "Tentativa",
                "type": "brand",
                "niche": "test",
                "tone": "test",
                "emoji_level": "low",
                "language": "pt-BR",
            },
        )
        assert resp.status_code == 403

    def test_editor_cannot_create_influencer(
        self, session: Session, editor_user: User, test_org: Organization
    ):
        client = make_client_for_user(session, editor_user)
        resp = client.post(
            f"/influencers?org_id={test_org.id}",
            json={
                "name": "Tentativa",
                "type": "brand",
                "niche": "test",
                "tone": "test",
                "emoji_level": "low",
                "language": "pt-BR",
            },
        )
        assert resp.status_code == 403

    def test_editor_cannot_update_influencer(
        self, session: Session, editor_user: User, test_influencer: Influencer
    ):
        client = make_client_for_user(session, editor_user)
        resp = client.patch(f"/influencers/{test_influencer.id}", json={"name": "Hack"})
        assert resp.status_code == 403


# ==========================================
# Cross-Org Isolation
# ==========================================


class TestCrossOrgIsolation:
    """Outsider (sem org) recebe 403 ao tentar operar."""

    def test_outsider_cannot_create_content(
        self, session: Session, outsider_user: User, test_cc: CostCenter, test_influencer: Influencer
    ):
        client = make_client_for_user(session, outsider_user)
        resp = client.post("/content-items", json={
            "cost_center_id": test_cc.id,
            "influencer_id": test_influencer.id,
            "provider_target": "instagram",
            "text": "Intruso",
        })
        assert resp.status_code == 403

    def test_outsider_cannot_create_influencer(
        self, session: Session, outsider_user: User, test_org: Organization
    ):
        client = make_client_for_user(session, outsider_user)
        resp = client.post(
            f"/influencers?org_id={test_org.id}",
            json={
                "name": "Intruso",
                "type": "brand",
                "niche": "test",
                "tone": "test",
                "emoji_level": "low",
                "language": "pt-BR",
            },
        )
        assert resp.status_code == 403
