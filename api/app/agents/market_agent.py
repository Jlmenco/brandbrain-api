"""Market Intelligence Agent — Source collection, findings, briefs.

Handles:
- run_market_collection: collect market data and create findings
- run_weekly_brief: consolidate weekly findings into brief + content briefs
"""

import uuid
from datetime import datetime, date, timedelta

from sqlmodel import Session, select

from app.models.user import User
from app.models.market import MarketSource, MarketFinding, MarketBrief, ContentBrief
from app.schemas.market import MarketRunRequest, MarketRunResponse, WeeklyBriefRequest, WeeklyBriefResponse
from app.services.ai_gateway import get_gateway


def run_market_collection(db: Session, user: User, req: MarketRunRequest) -> MarketRunResponse:
    """Collect market intelligence and create findings."""
    gateway = get_gateway()

    # Get active sources
    stmt = select(MarketSource).where(
        MarketSource.org_id == req.org_id,
        MarketSource.is_active == True,
    )
    if req.cc_id:
        stmt = stmt.where(
            (MarketSource.cost_center_id == req.cc_id) | (MarketSource.cost_center_id == None)
        )
    sources = db.exec(stmt).all()

    keywords = req.keywords or ["marketing", "tendências", "mercado"]

    # Generate mock findings based on keywords
    findings_data = []
    finding_types = ["trend", "opportunity", "faq", "competitor", "risk"]

    for i, kw in enumerate(keywords[:5]):
        finding = MarketFinding(
            org_id=req.org_id,
            cost_center_id=req.cc_id,
            title=f"[AI] Tendência detectada: {kw}",
            summary=f"Análise de mercado identificou movimentação relevante no tema '{kw}'. "
                    f"Fontes públicas indicam crescimento de interesse nos últimos 7 dias.",
            tags=[kw, "mercado", "tendência"],
            source_url=f"https://trends.example.com/{kw.replace(' ', '-')}",
            source_published_at=datetime.utcnow(),
            extracted_evidence=f"Evidência extraída sobre {kw} de fontes públicas.",
            confidence=0.7 + (i * 0.05),
            type=finding_types[i % len(finding_types)],
        )
        db.add(finding)
        db.flush()
        findings_data.append({
            "id": finding.id,
            "title": finding.title,
            "type": finding.type,
            "confidence": finding.confidence,
        })

    db.commit()

    return MarketRunResponse(
        findings_created=len(findings_data),
        findings=findings_data,
    )


def run_weekly_brief(db: Session, user: User, req: WeeklyBriefRequest) -> WeeklyBriefResponse:
    """Consolidate weekly findings into a brief and generate content briefs."""
    gateway = get_gateway()

    # Get findings from last 7 days
    week_ago = datetime.utcnow() - timedelta(days=7)
    stmt = select(MarketFinding).where(
        MarketFinding.org_id == req.org_id,
        MarketFinding.created_at >= week_ago,
    )
    if req.cc_id:
        stmt = stmt.where(
            (MarketFinding.cost_center_id == req.cc_id) | (MarketFinding.cost_center_id == None)
        )
    findings = db.exec(stmt).all()

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    # Create brief
    brief_content = {
        "top_trends": [
            f.title for f in findings if f.type == "trend"
        ][:5],
        "top_questions": [
            f"[AI] Pergunta do público sobre {f.tags[0] if f.tags else 'tema geral'}"
            for f in findings if f.type == "faq"
        ][:5],
        "content_ideas": [
            f"[AI] Ideia de conteúdo baseada em: {f.title}"
            for f in findings[:5]
        ],
        "campaign_opportunities": [
            f.title for f in findings if f.type == "opportunity"
        ][:3],
        "risks_to_avoid": [
            f.title for f in findings if f.type == "risk"
        ][:3],
        "sources": [
            {"title": f.title, "url": f.source_url, "confidence": f.confidence}
            for f in findings
        ],
        "findings_count": len(findings),
    }

    brief = MarketBrief(
        org_id=req.org_id,
        cost_center_id=req.cc_id,
        week_start=week_start,
        week_end=week_end,
        content=brief_content,
    )
    db.add(brief)
    db.flush()

    # Generate content briefs from top findings
    content_briefs_created = 0
    for f in findings[:5]:
        cb = ContentBrief(
            org_id=req.org_id,
            cost_center_id=req.cc_id,
            based_on_finding_ids=[f.id],
            title=f"Post sobre: {f.title}",
            thesis=f"[AI] Tese gerada a partir da tendência: {f.summary[:100]}",
            arguments=[
                "[AI] Argumento 1 baseado em dados de mercado",
                "[AI] Argumento 2 com prova social",
                "[AI] Argumento 3 com evidência de fonte",
            ],
            proof={"text": f.extracted_evidence, "source_url": f.source_url, "date": str(f.source_published_at)},
            format_suggestions={"linkedin": "post longo educativo", "instagram": "carrossel 5 slides"},
            cta_suggestion="Comente sua opinião sobre isso!",
        )
        db.add(cb)
        content_briefs_created += 1

    db.commit()

    return WeeklyBriefResponse(
        brief_id=brief.id,
        content=brief_content,
        content_briefs_created=content_briefs_created,
    )
