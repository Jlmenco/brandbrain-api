"""Testes para endpoints de organizacoes: setup-solo, upgrade, group-summary, filiais."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.user import User, OrgMember
from app.models.organization import Organization
from tests.conftest import make_client_for_user


# ---------------------------------------------------------------------------
# Fixtures auxiliares
# ---------------------------------------------------------------------------

@pytest.fixture(name="solo_org")
def solo_org_fixture(session: Session, test_user: User):
    org = Organization(id="solo-org-1", name="Minha Marca Solo", account_type="solo")
    session.add(org)
    session.flush()
    session.add(OrgMember(org_id=org.id, user_id=test_user.id, role="owner"))
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture(name="group_org")
def group_org_fixture(session: Session, test_user: User):
    org = Organization(id="group-org-1", name="Meu Grupo", account_type="group")
    session.add(org)
    session.flush()
    session.add(OrgMember(org_id=org.id, user_id=test_user.id, role="owner"))
    session.commit()
    session.refresh(org)
    return org


# ---------------------------------------------------------------------------
# GET /orgs — lista orgs com account_type
# ---------------------------------------------------------------------------

def test_list_orgs_returns_account_type(client: TestClient, test_org):
    resp = client.get("/orgs")
    assert resp.status_code == 200
    orgs = resp.json()
    assert len(orgs) >= 1
    org = next(o for o in orgs if o["id"] == test_org.id)
    assert "account_type" in org
    assert org["account_type"] == "agency"  # default


# ---------------------------------------------------------------------------
# POST /orgs/{id}/setup-solo
# ---------------------------------------------------------------------------

def test_setup_solo_success(client: TestClient, session: Session, solo_org):
    resp = client.post(
        f"/orgs/{solo_org.id}/setup-solo",
        json={"brand_name": "Joao Consultoria", "niche": "Financas"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["account_type"] == "solo"

    # Verifica que CostCenter foi criado
    from sqlmodel import select
    from app.models.cost_center import CostCenter
    ccs = session.exec(select(CostCenter).where(CostCenter.org_id == solo_org.id)).all()
    assert len(ccs) == 1
    assert ccs[0].name == "Joao Consultoria"

    # Verifica que Influencer foi criado
    from app.models.influencer import Influencer
    infs = session.exec(select(Influencer).where(Influencer.org_id == solo_org.id)).all()
    assert len(infs) == 1
    assert infs[0].type == "master"
    assert infs[0].niche == "Financas"


def test_setup_solo_requires_owner(session: Session, test_user: User, solo_org):
    """Editor nao pode chamar setup-solo."""
    editor = User(id="editor-solo", email="editor-solo@test.dev", name="Editor", hashed_password="x")
    session.add(editor)
    session.flush()
    session.add(OrgMember(org_id=solo_org.id, user_id=editor.id, role="editor"))
    session.commit()
    client = make_client_for_user(session, editor)
    resp = client.post(
        f"/orgs/{solo_org.id}/setup-solo",
        json={"brand_name": "Marca", "niche": "Tech"},
    )
    assert resp.status_code == 403


def test_setup_solo_rejects_agency_org(client: TestClient, test_org):
    """Orgs agency nao podem usar setup-solo."""
    resp = client.post(
        f"/orgs/{test_org.id}/setup-solo",
        json={"brand_name": "Teste", "niche": "Tech"},
    )
    assert resp.status_code == 400
    assert "Solo" in resp.json()["detail"]


def test_setup_solo_not_found(client: TestClient):
    resp = client.post(
        "/orgs/nonexistent/setup-solo",
        json={"brand_name": "X", "niche": "Y"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /orgs/{id}/upgrade
# ---------------------------------------------------------------------------

def test_upgrade_solo_to_agency(client: TestClient, solo_org):
    resp = client.post(
        f"/orgs/{solo_org.id}/upgrade",
        json={"target_type": "agency"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["account_type"] == "agency"


def test_upgrade_same_type_fails(client: TestClient, test_org):
    resp = client.post(
        f"/orgs/{test_org.id}/upgrade",
        json={"target_type": "agency"},
    )
    assert resp.status_code == 400
    assert "ja esta neste perfil" in resp.json()["detail"]


def test_upgrade_requires_owner(session: Session, test_user: User, solo_org):
    editor = User(id="editor-up", email="editor-up@test.dev", name="Editor", hashed_password="x")
    session.add(editor)
    session.flush()
    session.add(OrgMember(org_id=solo_org.id, user_id=editor.id, role="editor"))
    session.commit()
    client = make_client_for_user(session, editor)
    resp = client.post(
        f"/orgs/{solo_org.id}/upgrade",
        json={"target_type": "agency"},
    )
    assert resp.status_code == 403


def test_upgrade_not_found(client: TestClient):
    resp = client.post("/orgs/nonexistent/upgrade", json={"target_type": "agency"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /orgs/{id}/submit-review guard para Solo
# ---------------------------------------------------------------------------

def test_submit_review_blocked_for_solo(client: TestClient, session: Session, solo_org):
    """Solo org nao pode usar submit-review."""
    from app.models.cost_center import CostCenter
    from app.models.influencer import Influencer
    from app.models.content import ContentItem

    cc = CostCenter(id="cc-solo", org_id=solo_org.id, name="CC Solo", code="SOLO")
    session.add(cc)
    inf = Influencer(
        id="inf-solo", org_id=solo_org.id, type="master",
        name="Marca Solo", niche="Tech", tone="casual",
        emoji_level="low", language="pt-BR",
    )
    session.add(inf)
    ci = ContentItem(
        id="ci-solo", cost_center_id=cc.id, influencer_id=inf.id,
        provider_target="instagram", text="Post de teste", status="draft",
    )
    session.add(ci)
    session.commit()

    resp = client.post(f"/content-items/{ci.id}/submit-review")
    assert resp.status_code == 400
    assert "Solo" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# GET /orgs/{id}/group-summary
# ---------------------------------------------------------------------------

def test_group_summary_success(client: TestClient, group_org):
    resp = client.get(f"/orgs/{group_org.id}/group-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["group_id"] == group_org.id
    assert data["group_name"] == group_org.name
    assert "filiais" in data
    assert isinstance(data["filiais"], list)


def test_group_summary_rejects_agency(client: TestClient, test_org):
    resp = client.get(f"/orgs/{test_org.id}/group-summary")
    assert resp.status_code == 400


def test_group_summary_requires_admin(session: Session, test_user: User, group_org):
    editor = User(id="editor-g", email="editor-g@test.dev", name="Editor", hashed_password="x")
    session.add(editor)
    session.flush()
    session.add(OrgMember(org_id=group_org.id, user_id=editor.id, role="editor"))
    session.commit()
    client = make_client_for_user(session, editor)
    resp = client.get(f"/orgs/{group_org.id}/group-summary")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /orgs/{id}/filiais
# ---------------------------------------------------------------------------

def test_create_filial_success(client: TestClient, session: Session, group_org):
    resp = client.post(
        f"/orgs/{group_org.id}/filiais",
        json={"name": "Loja Sul", "account_type": "agency"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Loja Sul"
    assert data["account_type"] == "agency"
    assert data["parent_org_id"] == group_org.id


def test_create_filial_rejects_non_group(client: TestClient, test_org):
    resp = client.post(
        f"/orgs/{test_org.id}/filiais",
        json={"name": "Filial", "account_type": "agency"},
    )
    assert resp.status_code == 400


def test_create_filial_requires_owner(session: Session, test_user: User, group_org):
    editor = User(id="editor-f", email="editor-f@test.dev", name="Editor", hashed_password="x")
    session.add(editor)
    session.flush()
    session.add(OrgMember(org_id=group_org.id, user_id=editor.id, role="editor"))
    session.commit()
    client = make_client_for_user(session, editor)
    resp = client.post(
        f"/orgs/{group_org.id}/filiais",
        json={"name": "Filial", "account_type": "agency"},
    )
    assert resp.status_code == 403
