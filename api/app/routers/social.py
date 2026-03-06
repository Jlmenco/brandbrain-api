from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models.social import SocialAccount
from app.schemas.social import SocialAccountResponse
from app.dependencies import get_current_user

router = APIRouter()


@router.get("/{provider}/connect")
def connect(provider: str, cc_id: str = Query(...)):
    """Placeholder: redirect to OAuth flow."""
    return {"detail": f"OAuth flow for {provider} not yet implemented. Would redirect to {provider} OAuth page for cc_id={cc_id}"}


@router.get("/{provider}/callback")
def callback(provider: str, code: str = Query("")):
    """Placeholder: handle OAuth callback."""
    return {"detail": f"OAuth callback for {provider} received. Token exchange not yet implemented."}


@router.get("/accounts", response_model=list[SocialAccountResponse])
def list_accounts(cc_id: str = Query(...), db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    return db.exec(select(SocialAccount).where(SocialAccount.cost_center_id == cc_id)).all()


@router.post("/accounts/{account_id}/disconnect")
def disconnect(account_id: str, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    sa = db.get(SocialAccount, account_id)
    if not sa:
        raise HTTPException(status_code=404, detail="Social account not found")
    sa.status = "revoked"
    db.add(sa)
    db.commit()
    return {"detail": "Disconnected", "id": sa.id}
