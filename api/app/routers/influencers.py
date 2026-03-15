import json
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models.influencer import Influencer, BrandKit, InfluencerAsset
from app.schemas.influencer import (
    InfluencerCreate, InfluencerUpdate, InfluencerResponse,
    BrandKitCreate, BrandKitResponse,
)
from app.dependencies import get_current_user, check_role, ADMIN_ROLES

logger = logging.getLogger("app.influencers")

router = APIRouter()

ASSETS_DIR = Path(settings.STORAGE_BASE_PATH) / "avatars"


@router.get("", response_model=list[InfluencerResponse])
def list_influencers(org_id: str = Query(...), db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    return db.exec(select(Influencer).where(Influencer.org_id == org_id)).all()


@router.post("", response_model=InfluencerResponse)
def create_influencer(body: InfluencerCreate, org_id: str = Query(...), db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    check_role(db, current_user.id, org_id, ADMIN_ROLES)
    inf = Influencer(org_id=org_id, **body.model_dump())
    db.add(inf)
    db.commit()
    db.refresh(inf)
    # Auto-complete onboarding step
    try:
        from app.services.onboarding_service import complete_step
        complete_step(db, current_user.id, org_id, "first_influencer")
    except Exception:
        pass
    return inf


@router.get("/{influencer_id}", response_model=InfluencerResponse)
def get_influencer(influencer_id: str, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    inf = db.get(Influencer, influencer_id)
    if not inf:
        raise HTTPException(status_code=404, detail="Influencer not found")
    return inf


@router.patch("/{influencer_id}", response_model=InfluencerResponse)
def update_influencer(influencer_id: str, body: InfluencerUpdate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    inf = db.get(Influencer, influencer_id)
    if not inf:
        raise HTTPException(status_code=404, detail="Influencer not found")
    check_role(db, current_user.id, inf.org_id, ADMIN_ROLES)
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(inf, key, val)
    db.add(inf)
    db.commit()
    db.refresh(inf)
    return inf


@router.post("/{influencer_id}/brand-kit", response_model=BrandKitResponse)
def upsert_brand_kit(influencer_id: str, body: BrandKitCreate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    inf = db.get(Influencer, influencer_id)
    if not inf:
        raise HTTPException(status_code=404, detail="Influencer not found")
    check_role(db, current_user.id, inf.org_id, ADMIN_ROLES)
    existing = db.exec(select(BrandKit).where(BrandKit.influencer_id == influencer_id)).first()
    if existing:
        for key, val in body.model_dump().items():
            setattr(existing, key, val)
        db.add(existing)
        db.commit()
        db.refresh(existing)
        _auto_embed(db, influencer_id)
        return existing
    bk = BrandKit(influencer_id=influencer_id, **body.model_dump())
    db.add(bk)
    db.commit()
    db.refresh(bk)
    _auto_embed(db, influencer_id)
    # Auto-complete onboarding step
    try:
        from app.services.onboarding_service import complete_step
        complete_step(db, current_user.id, inf.org_id, "brand_kit")
    except Exception:
        pass
    return bk


def _auto_embed(db: Session, influencer_id: str):
    """Auto-embed brand kit content after upsert. Failure does not block save."""
    try:
        from app.services.embedding_service import get_embedding_service
        svc = get_embedding_service()
        svc.embed_brand_kit(db, influencer_id)
        db.commit()
    except Exception:
        db.rollback()


@router.get("/{influencer_id}/brand-kit", response_model=BrandKitResponse)
def get_brand_kit(influencer_id: str, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    bk = db.exec(select(BrandKit).where(BrandKit.influencer_id == influencer_id)).first()
    if not bk:
        raise HTTPException(status_code=404, detail="Brand kit not found")
    return bk


# --- Avatar Generation ---

def _build_avatar_prompt(inf: Influencer, bk: BrandKit | None) -> str:
    """Monta prompt para DALL-E baseado nos dados do influenciador."""
    parts = [
        "Photorealistic portrait photograph of a real human person who is the face of a brand called",
        f'"{inf.name}".',
        f"This person works in the {inf.niche} industry." if inf.niche else "",
        f"Their personality is {inf.tone}." if inf.tone else "",
    ]

    if bk:
        if bk.description:
            parts.append(f"Brand context: {bk.description}.")
        if bk.audience:
            aud = json.dumps(bk.audience, ensure_ascii=False)[:200]
            parts.append(f"Their audience is: {aud}.")
        if bk.style_guidelines:
            style = json.dumps(bk.style_guidelines, ensure_ascii=False)[:150]
            parts.append(f"Visual style: {style}.")

    parts.append(
        "Shot with a Canon EOS R5, 85mm f/1.4 lens, soft natural lighting. "
        "Head and shoulders portrait, shallow depth of field, neutral studio background. "
        "The person looks confident, approachable, and professional. "
        "Ultra realistic photograph, NOT an illustration or digital art. "
        "Square crop, suitable as a social media profile picture."
    )

    return " ".join(p for p in parts if p)


@router.post("/{influencer_id}/generate-avatar")
async def generate_avatar(
    influencer_id: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Gera avatar com IA (DALL-E 3) baseado nos dados do influenciador."""
    inf = db.get(Influencer, influencer_id)
    if not inf:
        raise HTTPException(status_code=404, detail="Influencer not found")
    check_role(db, current_user.id, inf.org_id, ADMIN_ROLES)

    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY nao configurada. Necessaria para gerar avatar.")

    # Verificar quota mensal de avatar
    from app.services.usage_service import check_quota
    check_quota(db, inf.org_id, "avatar")

    # Buscar brand kit para enriquecer o prompt
    bk = db.exec(select(BrandKit).where(BrandKit.influencer_id == influencer_id)).first()
    prompt = _build_avatar_prompt(inf, bk)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url
        revised_prompt = response.data[0].revised_prompt or ""

        # Download da imagem e salvar localmente
        import httpx
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{influencer_id}_{uuid.uuid4().hex[:8]}.png"
        filepath = ASSETS_DIR / filename

        with httpx.Client(timeout=30) as http:
            img_resp = http.get(image_url)
            img_resp.raise_for_status()
            filepath.write_bytes(img_resp.content)

        # Salvar/atualizar InfluencerAsset
        storage_url = f"/influencers/{influencer_id}/avatar"
        existing_asset = db.exec(
            select(InfluencerAsset).where(
                InfluencerAsset.influencer_id == influencer_id,
                InfluencerAsset.asset_type == "avatar",
            )
        ).first()

        if existing_asset:
            # Remover arquivo antigo
            old_path = ASSETS_DIR / existing_asset.metadata_json.get("filename", "")
            if old_path.exists():
                old_path.unlink()
            existing_asset.storage_url = storage_url
            existing_asset.metadata_json = {
                "filename": filename,
                "prompt": prompt[:500],
                "revised_prompt": revised_prompt[:500],
                "model": "dall-e-3",
            }
            db.add(existing_asset)
        else:
            asset = InfluencerAsset(
                influencer_id=influencer_id,
                asset_type="avatar",
                storage_url=storage_url,
                metadata_json={
                    "filename": filename,
                    "prompt": prompt[:500],
                    "revised_prompt": revised_prompt[:500],
                    "model": "dall-e-3",
                },
            )
            db.add(asset)

        db.commit()

        # Registrar uso de DALL-E 3
        try:
            from app.services.usage_service import log_usage
            log_usage(db, inf.org_id, "avatar", "dalle", 1, "images", user_id=current_user.id,
                      metadata={"influencer_id": influencer_id})
        except Exception:
            pass

        logger.info("Avatar gerado para influenciador %s: %s", influencer_id, filename)

        return {
            "url": storage_url,
            "filename": filename,
            "revised_prompt": revised_prompt,
        }

    except Exception as e:
        logger.error("Erro ao gerar avatar para %s: %s", influencer_id, str(e))
        raise HTTPException(status_code=500, detail=f"Erro ao gerar avatar: {str(e)}")


@router.get("/voices")
async def list_voices(current_user=Depends(get_current_user)):
    """Lista vozes disponíveis no ElevenLabs para configurar por influenciador."""
    from app.services.voice_service import VoiceService
    svc = VoiceService()
    voices = await svc.list_voices()
    return {"voices": voices}


@router.get("/{influencer_id}/avatar")
def get_avatar(influencer_id: str, db: Session = Depends(get_session)):
    """Serve a imagem do avatar do influenciador."""
    asset = db.exec(
        select(InfluencerAsset).where(
            InfluencerAsset.influencer_id == influencer_id,
            InfluencerAsset.asset_type == "avatar",
        )
    ).first()

    if not asset:
        raise HTTPException(status_code=404, detail="Avatar nao encontrado")

    filename = asset.metadata_json.get("filename", "")
    filepath = ASSETS_DIR / filename

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Arquivo de avatar nao encontrado")

    return FileResponse(filepath, media_type="image/png")
