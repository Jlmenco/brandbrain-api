from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.database import get_session
from app.config import settings
from app.services.auth_service import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

DbSession = Annotated[Session, Depends(get_session)]


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
):
    from app.models.user import User

    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_id = payload.get("sub")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


CurrentUser = Annotated["User", Depends(get_current_user)]

ADMIN_ROLES = ("owner", "admin")
EDITOR_ROLES = ("owner", "admin", "editor")


def check_role(db: Session, user_id: str, org_id: str, allowed_roles: tuple[str, ...]):
    """Raise 403 if user does not have one of allowed_roles in org."""
    from app.models.user import OrgMember

    member = db.exec(
        select(OrgMember).where(
            OrgMember.org_id == org_id,
            OrgMember.user_id == user_id,
        )
    ).first()
    if member is None or member.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of roles: {allowed_roles}",
        )


def require_role(*roles: str):
    """Dependency factory: ensures user has one of the given roles in the org."""

    def checker(
        current_user: CurrentUser,
        db: DbSession,
        org_id: str | None = None,
    ):
        from app.models.user import OrgMember

        if org_id is None:
            return current_user

        stmt = select(OrgMember).where(
            OrgMember.org_id == org_id,
            OrgMember.user_id == current_user.id,
        )
        member = db.exec(stmt).first()
        if member is None or member.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {roles}",
            )
        return current_user

    return checker
