import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select
from typing import Optional

from app.database import get_session
from app.models.template import ContentTemplate
from app.dependencies import get_current_user, check_role, ADMIN_ROLES, EDITOR_ROLES

logger = logging.getLogger("app.templates")

router = APIRouter()


class TemplateCreate(BaseModel):
    name: str
    description: str = ""
    provider_target: str = ""
    text_template: str
    tags: list = []


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    provider_target: Optional[str] = None
    text_template: Optional[str] = None
    tags: Optional[list] = None
    is_active: Optional[bool] = None


class TemplateResponse(BaseModel):
    id: str
    org_id: str
    name: str
    description: str
    provider_target: str
    text_template: str
    tags: list
    is_active: bool
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=list[TemplateResponse])
def list_templates(
    org_id: str = Query(...),
    provider: str = Query(None),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    stmt = select(ContentTemplate).where(
        ContentTemplate.org_id == org_id,
        ContentTemplate.is_active == True,  # noqa: E712
    )
    if provider:
        stmt = stmt.where(
            (ContentTemplate.provider_target == provider) |
            (ContentTemplate.provider_target == "")
        )
    return db.exec(stmt.order_by(ContentTemplate.name)).all()


@router.post("", response_model=TemplateResponse)
def create_template(
    body: TemplateCreate,
    org_id: str = Query(...),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    check_role(db, current_user.id, org_id, EDITOR_ROLES)
    tpl = ContentTemplate(
        org_id=org_id,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    tpl = db.get(ContentTemplate, template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tpl


@router.patch("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: str,
    body: TemplateUpdate,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    tpl = db.get(ContentTemplate, template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    check_role(db, current_user.id, tpl.org_id, EDITOR_ROLES)
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(tpl, key, val)
    tpl.updated_at = datetime.utcnow()
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    tpl = db.get(ContentTemplate, template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    check_role(db, current_user.id, tpl.org_id, ADMIN_ROLES)
    tpl.is_active = False
    tpl.updated_at = datetime.utcnow()
    db.add(tpl)
    db.commit()
