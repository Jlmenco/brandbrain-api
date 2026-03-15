from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user, check_role, ADMIN_ROLES
from app.models.cost_center import CostCenter
from app.services.report_service import generate_report_html, generate_report_pdf

router = APIRouter()


def _resolve_org_id(db: Session, cc_id: Optional[str]) -> Optional[str]:
    if not cc_id:
        return None
    cc = db.get(CostCenter, cc_id)
    return cc.org_id if cc else None


@router.get("/preview")
def preview_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    cc_id: Optional[str] = Query(None),
    org_id: Optional[str] = Query(None),
    report_type: str = Query("metrics_overview"),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Retorna preview HTML do relatorio."""
    resolved_org = org_id or _resolve_org_id(db, cc_id)
    if resolved_org:
        check_role(db, current_user.id, resolved_org, ADMIN_ROLES)

    html = generate_report_html(db, resolved_org or "", cc_id, date_from, date_to, report_type)
    return HTMLResponse(content=html)


@router.post("/generate")
def generate_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    cc_id: Optional[str] = Query(None),
    org_id: Optional[str] = Query(None),
    report_type: str = Query("metrics_overview"),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Gera relatorio PDF (ou HTML fallback se weasyprint nao disponivel)."""
    resolved_org = org_id or _resolve_org_id(db, cc_id)
    if resolved_org:
        check_role(db, current_user.id, resolved_org, ADMIN_ROLES)

    pdf_bytes = generate_report_pdf(db, resolved_org or "", cc_id, date_from, date_to, report_type)

    # Detect if it's actual PDF or HTML fallback
    is_pdf = pdf_bytes[:5] == b"%PDF-"
    if is_pdf:
        filename = f"brandbrain_report_{date_from}_{date_to}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    else:
        filename = f"brandbrain_report_{date_from}_{date_to}.html"
        return Response(
            content=pdf_bytes,
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
