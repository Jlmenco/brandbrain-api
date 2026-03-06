from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models.organization import Organization
from app.models.user import OrgMember
from app.schemas.organization import OrgCreate, OrgResponse, OrgMemberCreate, OrgMemberResponse
from app.dependencies import get_current_user

router = APIRouter()


@router.get("", response_model=list[OrgResponse])
def list_orgs(db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    memberships = db.exec(select(OrgMember).where(OrgMember.user_id == current_user.id)).all()
    if not memberships:
        return []
    org_ids = [m.org_id for m in memberships]
    role_map = {m.org_id: m.role for m in memberships}
    orgs = db.exec(select(Organization).where(Organization.id.in_(org_ids))).all()
    return [
        OrgResponse(id=org.id, name=org.name, role=role_map.get(org.id))
        for org in orgs
    ]


@router.post("", response_model=OrgResponse)
def create_org(body: OrgCreate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    org = Organization(name=body.name)
    db.add(org)
    db.flush()
    member = OrgMember(org_id=org.id, user_id=current_user.id, role="owner")
    db.add(member)
    db.commit()
    db.refresh(org)
    return org


@router.get("/{org_id}", response_model=OrgResponse)
def get_org(org_id: str, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.post("/{org_id}/members", response_model=OrgMemberResponse)
def add_member(org_id: str, body: OrgMemberCreate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    member = OrgMember(org_id=org_id, user_id=body.user_id, role=body.role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member
