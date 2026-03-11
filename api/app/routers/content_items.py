import logging
from datetime import datetime
from pathlib import Path

import redis as redis_lib
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models.content import ContentItem, Approval
from sqlalchemy import func
from app.schemas.content import ContentItemCreate, ContentItemUpdate, ContentItemResponse, PaginatedContentResponse, ScheduleRequest
from app.dependencies import get_current_user, check_role, ADMIN_ROLES, EDITOR_ROLES
from app.services.compliance import validate_content
from app.services.audit_service import log_action
from app.services.notification_service import notify_status_change
from app.models.influencer import Influencer, InfluencerAsset
from app.models.cost_center import CostCenter

logger = logging.getLogger(__name__)

router = APIRouter()

def _get_org_id(db: Session, cost_center_id: str) -> str:
    """Resolve org_id from a cost_center_id."""
    cc = db.get(CostCenter, cost_center_id)
    if not cc:
        raise HTTPException(status_code=404, detail="Cost center not found")
    return cc.org_id


VALID_TRANSITIONS = {
    "draft": ["review"],
    "review": ["approved", "draft"],
    "approved": ["scheduled", "draft"],
    "scheduled": ["publishing", "posted", "failed", "draft"],
    "publishing": ["posted", "failed"],
    "posted": [],
    "failed": ["draft", "publishing"],
}


@router.get("", response_model=PaginatedContentResponse)
def list_content_items(
    cc_id: str = Query(None),
    status: str = Query(None),
    provider: str = Query(None),
    search: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    stmt = select(ContentItem)
    if cc_id:
        stmt = stmt.where(ContentItem.cost_center_id == cc_id)
    if status:
        stmt = stmt.where(ContentItem.status == status)
    if provider:
        stmt = stmt.where(ContentItem.provider_target == provider)
    if search:
        stmt = stmt.where(ContentItem.text.ilike(f"%{search}%"))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.exec(count_stmt).one()

    stmt = stmt.order_by(ContentItem.created_at.desc()).offset(skip).limit(limit)
    items = db.exec(stmt).all()
    return {"items": items, "total": total}


@router.post("", response_model=ContentItemResponse)
def create_content_item(body: ContentItemCreate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    org_id = _get_org_id(db, body.cost_center_id)
    check_role(db, current_user.id, org_id, EDITOR_ROLES)
    ci = ContentItem(**body.model_dump())
    db.add(ci)
    db.commit()
    db.refresh(ci)
    log_action(db, org_id, ci.cost_center_id, current_user.id, "create", "content_item", ci.id)
    return ci


@router.get("/{item_id}", response_model=ContentItemResponse)
def get_content_item(item_id: str, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    ci = db.get(ContentItem, item_id)
    if not ci:
        raise HTTPException(status_code=404, detail="Content item not found")
    return ci


@router.patch("/{item_id}", response_model=ContentItemResponse)
def update_content_item(item_id: str, body: ContentItemUpdate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    ci = db.get(ContentItem, item_id)
    if not ci:
        raise HTTPException(status_code=404, detail="Content item not found")
    org_id = _get_org_id(db, ci.cost_center_id)
    check_role(db, current_user.id, org_id, EDITOR_ROLES)
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(ci, key, val)
    ci.updated_at = datetime.utcnow()
    ci.version += 1
    db.add(ci)
    db.commit()
    db.refresh(ci)
    log_action(db, org_id, ci.cost_center_id, current_user.id, "update", "content_item", ci.id)
    return ci


@router.post("/{item_id}/submit-review")
def submit_review(item_id: str, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    ci = db.get(ContentItem, item_id)
    if not ci:
        raise HTTPException(status_code=404, detail="Content item not found")
    org_id = _get_org_id(db, ci.cost_center_id)
    check_role(db, current_user.id, org_id, EDITOR_ROLES)
    if ci.status != "draft":
        raise HTTPException(status_code=400, detail="Can only submit drafts for review")
    # Run compliance check
    inf = db.get(Influencer, ci.influencer_id)
    if inf:
        result = validate_content(ci.text, inf)
        if not result["valid"]:
            raise HTTPException(status_code=422, detail={"compliance_issues": result["issues"]})
    ci.status = "review"
    ci.updated_at = datetime.utcnow()
    db.add(ci)
    db.commit()
    log_action(db, org_id, ci.cost_center_id, current_user.id, "submit_review", "content_item", ci.id)
    notify_status_change(db, org_id, "submit_review", ci.id, current_user.id, ci.text)
    return {"status": "review", "id": ci.id}


@router.post("/{item_id}/approve")
def approve(item_id: str, notes: str = "", db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    ci = db.get(ContentItem, item_id)
    if not ci:
        raise HTTPException(status_code=404, detail="Content item not found")
    org_id = _get_org_id(db, ci.cost_center_id)
    check_role(db, current_user.id, org_id, ADMIN_ROLES)
    if ci.status != "review":
        raise HTTPException(status_code=400, detail="Can only approve items in review")
    approval = Approval(content_item_id=ci.id, reviewer_user_id=current_user.id, decision="approve", notes=notes)
    ci.status = "approved"
    ci.updated_at = datetime.utcnow()
    db.add(approval)
    db.add(ci)
    db.commit()
    log_action(db, org_id, ci.cost_center_id, current_user.id, "approve", "content_item", ci.id, {"notes": notes} if notes else None)
    notify_status_change(db, org_id, "approve", ci.id, current_user.id, ci.text)
    return {"status": "approved", "id": ci.id}


@router.post("/{item_id}/request-changes")
def request_changes(item_id: str, notes: str = "", db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    ci = db.get(ContentItem, item_id)
    if not ci:
        raise HTTPException(status_code=404, detail="Content item not found")
    org_id = _get_org_id(db, ci.cost_center_id)
    check_role(db, current_user.id, org_id, ADMIN_ROLES)
    if ci.status != "review":
        raise HTTPException(status_code=400, detail="Can only request changes for items in review")
    approval = Approval(content_item_id=ci.id, reviewer_user_id=current_user.id, decision="request_changes", notes=notes)
    ci.status = "draft"
    ci.updated_at = datetime.utcnow()
    db.add(approval)
    db.add(ci)
    db.commit()
    log_action(db, org_id, ci.cost_center_id, current_user.id, "request_changes", "content_item", ci.id, {"notes": notes} if notes else None)
    notify_status_change(db, org_id, "request_changes", ci.id, current_user.id, ci.text)
    return {"status": "draft", "id": ci.id, "notes": notes}


@router.post("/{item_id}/reject")
def reject(item_id: str, notes: str = "", db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    ci = db.get(ContentItem, item_id)
    if not ci:
        raise HTTPException(status_code=404, detail="Content item not found")
    org_id = _get_org_id(db, ci.cost_center_id)
    check_role(db, current_user.id, org_id, ADMIN_ROLES)
    if ci.status != "review":
        raise HTTPException(status_code=400, detail="Can only reject items in review")
    approval = Approval(content_item_id=ci.id, reviewer_user_id=current_user.id, decision="reject", notes=notes)
    ci.status = "rejected"
    ci.updated_at = datetime.utcnow()
    db.add(approval)
    db.add(ci)
    db.commit()
    log_action(db, org_id, ci.cost_center_id, current_user.id, "reject", "content_item", ci.id, {"notes": notes} if notes else None)
    notify_status_change(db, org_id, "reject", ci.id, current_user.id, ci.text)
    return {"status": "rejected", "id": ci.id}


@router.post("/{item_id}/schedule")
def schedule(item_id: str, body: ScheduleRequest, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    ci = db.get(ContentItem, item_id)
    if not ci:
        raise HTTPException(status_code=404, detail="Content item not found")
    org_id = _get_org_id(db, ci.cost_center_id)
    check_role(db, current_user.id, org_id, ADMIN_ROLES)
    if ci.status != "approved":
        raise HTTPException(status_code=400, detail="Can only schedule approved items")
    ci.status = "scheduled"
    ci.scheduled_at = body.scheduled_at
    ci.retry_count = 0
    ci.next_retry_at = None
    ci.last_error = None
    ci.updated_at = datetime.utcnow()
    db.add(ci)
    db.commit()
    log_action(db, org_id, ci.cost_center_id, current_user.id, "schedule", "content_item", ci.id, {"scheduled_at": str(body.scheduled_at)})
    notify_status_change(db, org_id, "schedule", ci.id, current_user.id, ci.text)
    return {"status": "scheduled", "id": ci.id, "scheduled_at": str(ci.scheduled_at)}


def _signal_worker(content_item_id: str) -> None:
    """Send a Redis signal to wake the worker for immediate processing."""
    try:
        r = redis_lib.from_url(settings.REDIS_URL)
        r.publish("bb:publish_signal", content_item_id)
        r.close()
    except Exception:
        logger.warning("Could not signal worker via Redis, will be picked up on next poll")


@router.post("/{item_id}/publish-now")
def publish_now(item_id: str, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    ci = db.get(ContentItem, item_id)
    if not ci:
        raise HTTPException(status_code=404, detail="Content item not found")
    org_id = _get_org_id(db, ci.cost_center_id)
    check_role(db, current_user.id, org_id, ADMIN_ROLES)
    if ci.status not in ("approved", "scheduled"):
        raise HTTPException(status_code=400, detail="Can only publish approved or scheduled items")
    # Delegate to worker for actual publishing
    ci.status = "publishing"
    ci.scheduled_at = datetime.utcnow()
    ci.retry_count = 0
    ci.next_retry_at = None
    ci.last_error = None
    ci.updated_at = datetime.utcnow()
    db.add(ci)
    db.commit()

    log_action(db, org_id, ci.cost_center_id, current_user.id, "publish_now", "content_item", ci.id)
    notify_status_change(db, org_id, "publish_now", ci.id, current_user.id, ci.text)
    _signal_worker(ci.id)
    return {"status": "publishing", "id": ci.id}


# --- Video Generation ---

VIDEOS_DIR = Path(settings.STORAGE_BASE_PATH) / "videos"


@router.post("/{content_id}/generate-video")
async def generate_video(
    content_id: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Gera video lip-sync do influenciador falando o texto do conteudo.

    Pipeline: Avatar (DALL-E 3) + Voz (ElevenLabs) + Video (Hedra).
    Usa RAG context via brand kit embeddings do influenciador.
    """
    ci = db.get(ContentItem, content_id)
    if not ci:
        raise HTTPException(status_code=404, detail="Content item not found")

    org_id = _get_org_id(db, ci.cost_center_id)
    check_role(db, current_user.id, org_id, EDITOR_ROLES)

    if not ci.influencer_id:
        raise HTTPException(status_code=400, detail="Conteudo nao tem influenciador associado")

    # 1. Buscar avatar do influenciador
    avatar_asset = db.exec(
        select(InfluencerAsset).where(
            InfluencerAsset.influencer_id == ci.influencer_id,
            InfluencerAsset.asset_type == "avatar",
        )
    ).first()

    if not avatar_asset:
        raise HTTPException(
            status_code=400,
            detail="Influenciador nao tem avatar gerado. Gere o avatar primeiro.",
        )

    avatar_filename = avatar_asset.metadata_json.get("filename", "")
    avatar_path = Path(settings.STORAGE_BASE_PATH) / "avatars" / avatar_filename
    if not avatar_path.exists():
        raise HTTPException(status_code=400, detail="Arquivo de avatar nao encontrado no disco")

    image_bytes = avatar_path.read_bytes()

    # 2. Gerar voz com ElevenLabs
    from app.services.voice_service import VoiceService
    voice_svc = VoiceService()

    # Limitar texto para TTS (ElevenLabs tem limite de ~5000 chars)
    tts_text = ci.text[:5000]
    try:
        audio_bytes = await voice_svc.generate_speech(tts_text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao gerar voz: {e}")

    # 3. Gerar video lip-sync com Hedra
    from app.services.video_service import VideoService
    video_svc = VideoService()

    # Aspect ratio baseado na plataforma
    aspect_map = {
        "tiktok": "9:16",
        "instagram": "9:16",
        "youtube": "16:9",
        "linkedin": "1:1",
        "facebook": "1:1",
    }
    aspect_ratio = aspect_map.get(ci.provider_target, "9:16")

    try:
        video_url, video_bytes = await video_svc.generate_talking_video(
            image_bytes=image_bytes,
            audio_bytes=audio_bytes,
            aspect_ratio=aspect_ratio,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao gerar video: {e}")

    # 4. Salvar video localmente
    import uuid
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    video_filename = f"{content_id}_{uuid.uuid4().hex[:8]}.mp4"
    video_path = VIDEOS_DIR / video_filename
    video_path.write_bytes(video_bytes)

    # 5. Atualizar media_refs do conteudo
    media_refs = ci.media_refs or []
    # Remover videos anteriores
    media_refs = [m for m in media_refs if m.get("type") != "video"]
    media_refs.append({
        "type": "video",
        "url": f"/content/{content_id}/video",
        "filename": video_filename,
        "source": "hedra",
    })
    ci.media_refs = media_refs
    ci.updated_at = datetime.utcnow()
    db.add(ci)
    db.commit()

    log_action(db, org_id, ci.cost_center_id, current_user.id, "generate_video", "content_item", ci.id)

    return {
        "status": "success",
        "video_url": f"/content/{content_id}/video",
        "filename": video_filename,
    }


@router.get("/{content_id}/video")
async def get_video(
    content_id: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Retorna o video gerado de um conteudo."""
    ci = db.get(ContentItem, content_id)
    if not ci:
        raise HTTPException(status_code=404, detail="Content item not found")

    media_refs = ci.media_refs or []
    video_ref = next((m for m in media_refs if m.get("type") == "video"), None)
    if not video_ref:
        raise HTTPException(status_code=404, detail="Video nao encontrado")

    video_path = VIDEOS_DIR / video_ref["filename"]
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de video nao encontrado")

    return FileResponse(video_path, media_type="video/mp4")
