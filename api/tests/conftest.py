import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User, OrgMember
from app.models.organization import Organization
from app.models.cost_center import CostCenter
from app.models.influencer import Influencer, BrandKit
from app.models.content import ContentItem, Approval
from app.models.metrics import MetricsDaily
from app.models.notification import Notification
from app.models.drip import DripCampaign, DripStep, DripEnrollment
from app.models.onboarding import OnboardingProgress
from app.models.editorial import EditorialPlan, EditorialSlot
from app.services.auth_service import hash_password


# SQLite in-memory engine — StaticPool ensures a single shared connection
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Only the tables we actually need (avoids pgvector/other PG-specific models)
_test_tables = [
    "users",
    "org_members",
    "organizations",
    "cost_centers",
    "influencers",
    "brand_kits",
    "influencer_assets",
    "macro_contents",
    "content_items",
    "approvals",
    "metrics_daily",
    "campaigns",
    "audit_logs",
    "notifications",
    "content_templates",
    "usage_logs",
    "webhook_configs",
    "drip_campaigns",
    "drip_steps",
    "drip_enrollments",
    "onboarding_progress",
    "editorial_plans",
    "editorial_slots",
]


def _create_test_tables():
    tables = [
        t for t in SQLModel.metadata.sorted_tables if t.name in _test_tables
    ]
    SQLModel.metadata.create_all(test_engine, tables=tables)


def _drop_test_tables():
    tables = [
        t for t in SQLModel.metadata.sorted_tables if t.name in _test_tables
    ]
    SQLModel.metadata.drop_all(test_engine, tables=tables)


@pytest.fixture(name="session")
def session_fixture():
    _create_test_tables()
    with Session(test_engine) as session:
        yield session
    _drop_test_tables()


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    user = User(
        id="user-1",
        email="test@brandbrain.dev",
        name="Test User",
        hashed_password=hash_password("test123"),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="test_org")
def test_org_fixture(session: Session, test_user: User):
    org = Organization(id="org-1", name="Test Org")
    session.add(org)
    member = OrgMember(org_id="org-1", user_id=test_user.id, role="owner")
    session.add(member)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture(name="test_cc")
def test_cc_fixture(session: Session, test_org: Organization):
    cc = CostCenter(id="cc-1", org_id=test_org.id, name="Test CC", code="TESTCC")
    session.add(cc)
    session.commit()
    session.refresh(cc)
    return cc


@pytest.fixture(name="test_influencer")
def test_influencer_fixture(session: Session, test_org: Organization, test_cc: CostCenter):
    inf = Influencer(
        id="inf-1",
        org_id=test_org.id,
        cost_center_id=test_cc.id,
        type="brand",
        name="Test Influencer",
        niche="tech",
        tone="professional",
        emoji_level="low",
        forbidden_words=["spam", "gratis"],
        forbidden_topics=["politica"],
        allowed_words=["inovacao"],
        cta_style="Saiba mais",
        language="pt-BR",
    )
    session.add(inf)
    session.commit()
    session.refresh(inf)
    return inf


@pytest.fixture(name="test_content_item")
def test_content_item_fixture(
    session: Session, test_cc: CostCenter, test_influencer: Influencer
):
    ci = ContentItem(
        id="ci-1",
        cost_center_id=test_cc.id,
        influencer_id=test_influencer.id,
        provider_target="linkedin",
        text="Conteudo de teste para LinkedIn",
        status="draft",
    )
    session.add(ci)
    session.commit()
    session.refresh(ci)
    return ci


@pytest.fixture(name="editor_user")
def editor_user_fixture(session: Session, test_org: Organization):
    user = User(
        id="user-editor",
        email="editor@test.dev",
        name="Editor User",
        hashed_password=hash_password("test123"),
    )
    session.add(user)
    session.flush()
    session.add(OrgMember(org_id=test_org.id, user_id=user.id, role="editor"))
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="viewer_user")
def viewer_user_fixture(session: Session, test_org: Organization):
    user = User(
        id="user-viewer",
        email="viewer@test.dev",
        name="Viewer User",
        hashed_password=hash_password("test123"),
    )
    session.add(user)
    session.flush()
    session.add(OrgMember(org_id=test_org.id, user_id=user.id, role="viewer"))
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="outsider_user")
def outsider_user_fixture(session: Session):
    """User that belongs to no organization."""
    user = User(
        id="user-outsider",
        email="outsider@test.dev",
        name="Outsider",
        hashed_password=hash_password("test123"),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def make_client_for_user(session: Session, user: User) -> TestClient:
    """Create a TestClient authenticated as a specific user."""
    def get_session_override():
        yield session

    def get_current_user_override():
        return user

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_current_user] = get_current_user_override
    return TestClient(app)


@pytest.fixture(name="client")
def client_fixture(session: Session, test_user: User):
    def get_session_override():
        yield session

    def get_current_user_override():
        return test_user

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_current_user] = get_current_user_override

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
