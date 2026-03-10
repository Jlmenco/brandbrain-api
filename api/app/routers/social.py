"""
Social Integrations — OAuth connect/callback + gerenciamento de contas.
Suporta: LinkedIn, Meta (Facebook/Instagram), TikTok, YouTube.
"""
import os
import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
import httpx
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models.social import SocialAccount
from app.schemas.social import SocialAccountResponse
from app.dependencies import get_current_user, check_role, ADMIN_ROLES
from app.services.token_crypto import encrypt_token

logger = logging.getLogger("app.social")

router = APIRouter()

# --- Provider configs (env vars) ---
OAUTH_PROVIDERS = {
    "linkedin": {
        "client_id": os.getenv("LINKEDIN_CLIENT_ID", ""),
        "client_secret": os.getenv("LINKEDIN_CLIENT_SECRET", ""),
        "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
        "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
        "scopes": "openid profile w_member_social",
        "profile_url": "https://api.linkedin.com/v2/userinfo",
    },
    "meta": {
        "client_id": os.getenv("META_APP_ID", ""),
        "client_secret": os.getenv("META_APP_SECRET", ""),
        "auth_url": "https://www.facebook.com/v21.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v21.0/oauth/access_token",
        "scopes": "pages_manage_posts,pages_read_engagement,instagram_basic,instagram_content_publish",
        "profile_url": "https://graph.facebook.com/v21.0/me",
    },
    "tiktok": {
        "client_id": os.getenv("TIKTOK_CLIENT_KEY", ""),
        "client_secret": os.getenv("TIKTOK_CLIENT_SECRET", ""),
        "auth_url": "https://www.tiktok.com/v2/auth/authorize/",
        "token_url": "https://open.tiktokapis.com/v2/oauth/token/",
        "scopes": "user.info.basic,video.publish,video.upload",
        "profile_url": "https://open.tiktokapis.com/v2/user/info/",
    },
    "youtube": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube",
        "profile_url": "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
    },
}

# URL base para callbacks (ex: https://api.brandbrain.dev)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def _get_redirect_uri(provider: str) -> str:
    return f"{API_BASE_URL}/integrations/{provider}/callback"


# --- OAuth Connect ---

@router.get("/{provider}/connect")
def connect(
    provider: str,
    cc_id: str = Query(..., description="Cost center ID"),
    org_id: str = Query(..., description="Organization ID"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """Inicia fluxo OAuth — redireciona para o provider."""
    check_role(db, current_user.id, org_id, ADMIN_ROLES)

    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Provider '{provider}' nao suportado. Use: {list(OAUTH_PROVIDERS.keys())}")

    config = OAUTH_PROVIDERS[provider]
    if not config["client_id"]:
        raise HTTPException(status_code=400, detail=f"Credenciais OAuth para '{provider}' nao configuradas no servidor.")

    # State = org_id:cc_id (sera validado no callback)
    state = f"{org_id}:{cc_id}"
    redirect_uri = _get_redirect_uri(provider)

    if provider == "tiktok":
        params = {
            "client_key": config["client_id"],
            "scope": config["scopes"],
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
        }
    elif provider == "youtube":
        params = {
            "client_id": config["client_id"],
            "scope": config["scopes"],
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
    else:
        params = {
            "client_id": config["client_id"],
            "scope": config["scopes"],
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
        }

    auth_url = f"{config['auth_url']}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


# --- OAuth Callback ---

@router.get("/{provider}/callback")
def callback(
    provider: str,
    code: str = Query(""),
    state: str = Query(""),
    error: str = Query(""),
    db: Session = Depends(get_session),
):
    """Recebe callback OAuth, troca code por token, salva SocialAccount."""
    if error:
        logger.warning("OAuth error para %s: %s", provider, error)
        return RedirectResponse(url=f"{os.getenv('WEB_BASE_URL', 'http://localhost:3000')}/configuracoes?social_error={error}")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Parametros code e state obrigatorios")

    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Provider '{provider}' nao suportado")

    # Parse state
    parts = state.split(":", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="State invalido")
    org_id, cc_id = parts

    config = OAUTH_PROVIDERS[provider]
    redirect_uri = _get_redirect_uri(provider)

    # Trocar code por token
    token_data = _exchange_code(provider, config, code, redirect_uri)
    if not token_data:
        return RedirectResponse(url=f"{os.getenv('WEB_BASE_URL', 'http://localhost:3000')}/configuracoes?social_error=token_exchange_failed")

    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 0)

    # Buscar info do perfil
    profile = _fetch_profile(provider, config, access_token, token_data)
    account_id = profile.get("id", "")
    account_name = profile.get("name", "")

    # Para Meta, buscar long-lived token e paginas
    if provider == "meta":
        ll_data = _exchange_long_lived_token(config, access_token)
        if ll_data:
            access_token = ll_data.get("access_token", access_token)
            expires_in = ll_data.get("expires_in", expires_in)

    # Calcular expiracao
    from datetime import datetime, timedelta
    token_expires_at = None
    if expires_in:
        token_expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))

    # Upsert SocialAccount
    existing = db.exec(
        select(SocialAccount).where(
            SocialAccount.org_id == org_id,
            SocialAccount.cost_center_id == cc_id,
            SocialAccount.provider == provider,
        )
    ).first()

    if existing:
        existing.account_id = account_id
        existing.account_name = account_name
        existing.token_encrypted = encrypt_token(access_token)
        existing.refresh_token_encrypted = encrypt_token(refresh_token)
        existing.token_expires_at = token_expires_at
        existing.status = "connected"
        existing.scopes = config["scopes"].split(",") if "," in config["scopes"] else config["scopes"].split()
        db.add(existing)
    else:
        sa = SocialAccount(
            org_id=org_id,
            cost_center_id=cc_id,
            provider=provider,
            account_id=account_id,
            account_name=account_name,
            token_encrypted=encrypt_token(access_token),
            refresh_token_encrypted=encrypt_token(refresh_token),
            token_expires_at=token_expires_at,
            status="connected",
            scopes=config["scopes"].split(",") if "," in config["scopes"] else config["scopes"].split(),
        )
        db.add(sa)

    db.commit()
    logger.info("Conta %s conectada: %s (%s)", provider, account_name, account_id)

    return RedirectResponse(url=f"{os.getenv('WEB_BASE_URL', 'http://localhost:3000')}/configuracoes?social_connected={provider}")


def _exchange_code(provider: str, config: dict, code: str, redirect_uri: str) -> dict | None:
    """Troca authorization code por access token."""
    try:
        with httpx.Client(timeout=30) as client:
            if provider == "tiktok":
                resp = client.post(
                    config["token_url"],
                    data={
                        "client_key": config["client_id"],
                        "client_secret": config["client_secret"],
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri,
                    },
                )
            else:
                resp = client.post(
                    config["token_url"],
                    data={
                        "client_id": config["client_id"],
                        "client_secret": config["client_secret"],
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri,
                    },
                )
            data = resp.json()

            if "access_token" in data:
                return data
            # TikTok wrapper
            if "data" in data and "access_token" in data.get("data", {}):
                return data["data"]

            logger.error("Token exchange failed for %s: %s", provider, data)
            return None

    except httpx.HTTPError as e:
        logger.error("Token exchange HTTP error for %s: %s", provider, str(e))
        return None


def _fetch_profile(provider: str, config: dict, access_token: str, token_data: dict) -> dict:
    """Busca informacoes do perfil do usuario."""
    try:
        with httpx.Client(timeout=15) as client:
            if provider == "tiktok":
                resp = client.get(
                    config["profile_url"],
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"fields": "open_id,display_name"},
                )
                data = resp.json().get("data", {}).get("user", {})
                return {"id": data.get("open_id", ""), "name": data.get("display_name", "")}

            elif provider == "youtube":
                resp = client.get(
                    config["profile_url"],
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                items = resp.json().get("items", [])
                if items:
                    snippet = items[0].get("snippet", {})
                    return {"id": items[0].get("id", ""), "name": snippet.get("title", "")}
                return {"id": "", "name": ""}

            elif provider == "linkedin":
                resp = client.get(
                    config["profile_url"],
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                data = resp.json()
                return {"id": data.get("sub", ""), "name": data.get("name", "")}

            else:
                # Meta (Facebook)
                resp = client.get(
                    config["profile_url"],
                    params={"access_token": access_token, "fields": "id,name"},
                )
                return resp.json()

    except httpx.HTTPError as e:
        logger.error("Profile fetch error for %s: %s", provider, str(e))
        return {"id": "", "name": ""}


def _exchange_long_lived_token(config: dict, short_token: str) -> dict | None:
    """Meta: troca short-lived token por long-lived (60 dias)."""
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                "https://graph.facebook.com/v21.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": config["client_id"],
                    "client_secret": config["client_secret"],
                    "fb_exchange_token": short_token,
                },
            )
            data = resp.json()
            if "access_token" in data:
                return data
            return None
    except httpx.HTTPError:
        return None


# --- Account Management ---

@router.get("/accounts", response_model=list[SocialAccountResponse])
def list_accounts(
    cc_id: str = Query(...),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Lista contas sociais conectadas para um centro de custo."""
    return db.exec(
        select(SocialAccount).where(SocialAccount.cost_center_id == cc_id)
    ).all()


@router.post("/accounts/{account_id}/disconnect")
def disconnect(
    account_id: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Desconecta uma conta social (revoga status)."""
    sa = db.get(SocialAccount, account_id)
    if not sa:
        raise HTTPException(status_code=404, detail="Conta social nao encontrada")
    sa.status = "revoked"
    db.add(sa)
    db.commit()
    return {"detail": "Desconectada", "id": sa.id}


@router.delete("/accounts/{account_id}")
def delete_account(
    account_id: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Remove uma conta social permanentemente."""
    sa = db.get(SocialAccount, account_id)
    if not sa:
        raise HTTPException(status_code=404, detail="Conta social nao encontrada")
    db.delete(sa)
    db.commit()
    return {"detail": "Removida", "id": account_id}
