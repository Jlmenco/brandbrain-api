"""Report Service — Generates HTML/PDF reports from metrics data."""
import logging
from datetime import datetime, date
from typing import Optional

from sqlmodel import Session, select
from sqlalchemy import func

from app.models.content import ContentItem
from app.models.metrics import MetricsDaily

logger = logging.getLogger(__name__)


def generate_report_html(
    db: Session,
    org_id: str,
    cc_id: Optional[str],
    date_from: date,
    date_to: date,
    report_type: str = "metrics_overview",
) -> str:
    """Generate an HTML report with metrics and content performance data."""

    # Fetch metrics joined with content items for provider/cost_center info
    stmt = (
        select(MetricsDaily, ContentItem)
        .join(ContentItem, MetricsDaily.content_item_id == ContentItem.id)
        .where(
            MetricsDaily.date >= date_from,
            MetricsDaily.date <= date_to,
        )
    )
    if cc_id:
        stmt = stmt.where(ContentItem.cost_center_id == cc_id)

    results = db.exec(stmt.order_by(MetricsDaily.date.asc())).all()

    # Fetch content stats
    content_stmt = select(ContentItem).where(
        ContentItem.created_at >= datetime.combine(date_from, datetime.min.time()),
        ContentItem.created_at <= datetime.combine(date_to, datetime.max.time()),
    )
    if cc_id:
        content_stmt = content_stmt.where(ContentItem.cost_center_id == cc_id)

    content_items = db.exec(content_stmt).all()

    # Aggregate metrics
    total_followers_delta = 0
    total_impressions = 0
    total_engagements = 0
    total_clicks = 0
    metrics_by_provider: dict[str, dict] = {}

    for m, ci in results:
        engagements = (m.likes or 0) + (m.comments or 0) + (m.shares or 0)
        total_followers_delta += m.followers_delta or 0
        total_impressions += m.impressions or 0
        total_engagements += engagements
        total_clicks += m.clicks or 0

        provider = ci.provider_target
        if provider not in metrics_by_provider:
            metrics_by_provider[provider] = {
                "impressions": 0, "engagements": 0, "clicks": 0, "followers_delta": 0,
            }
        metrics_by_provider[provider]["impressions"] += m.impressions or 0
        metrics_by_provider[provider]["engagements"] += engagements
        metrics_by_provider[provider]["clicks"] += m.clicks or 0
        metrics_by_provider[provider]["followers_delta"] += m.followers_delta or 0

    # Content stats
    status_counts: dict[str, int] = {}
    platform_counts: dict[str, int] = {}
    for ci in content_items:
        status_counts[ci.status] = status_counts.get(ci.status, 0) + 1
        platform_counts[ci.provider_target] = platform_counts.get(ci.provider_target, 0) + 1

    engagement_rate = (
        round((total_engagements / total_impressions) * 100, 2)
        if total_impressions > 0 else 0
    )

    # Build HTML
    period_label = f"{date_from.strftime('%d/%m/%Y')} a {date_to.strftime('%d/%m/%Y')}"

    provider_rows = ""
    for prov, data in sorted(metrics_by_provider.items()):
        prov_rate = round((data["engagements"] / data["impressions"]) * 100, 2) if data["impressions"] > 0 else 0
        provider_rows += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #e5e7eb;">{prov.title()}</td>
          <td style="padding:8px;border-bottom:1px solid #e5e7eb;text-align:right;">{data['followers_delta']:+,}</td>
          <td style="padding:8px;border-bottom:1px solid #e5e7eb;text-align:right;">{data['impressions']:,}</td>
          <td style="padding:8px;border-bottom:1px solid #e5e7eb;text-align:right;">{data['engagements']:,}</td>
          <td style="padding:8px;border-bottom:1px solid #e5e7eb;text-align:right;">{data['clicks']:,}</td>
          <td style="padding:8px;border-bottom:1px solid #e5e7eb;text-align:right;">{prov_rate}%</td>
        </tr>"""

    status_rows = ""
    for st, count in sorted(status_counts.items()):
        status_rows += f"""
        <tr>
          <td style="padding:6px;border-bottom:1px solid #e5e7eb;">{st.title()}</td>
          <td style="padding:6px;border-bottom:1px solid #e5e7eb;text-align:right;">{count}</td>
        </tr>"""

    platform_rows = ""
    for plat, count in sorted(platform_counts.items()):
        platform_rows += f"""
        <tr>
          <td style="padding:6px;border-bottom:1px solid #e5e7eb;">{plat.title()}</td>
          <td style="padding:6px;border-bottom:1px solid #e5e7eb;text-align:right;">{count}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         margin: 0; padding: 40px; color: #111827; background: #fff; }}
  .header {{ display: flex; justify-content: space-between; align-items: center;
             border-bottom: 3px solid #6d28d9; padding-bottom: 16px; margin-bottom: 32px; }}
  .logo {{ font-size: 24px; font-weight: 700; color: #6d28d9; }}
  .period {{ font-size: 14px; color: #6b7280; }}
  h2 {{ font-size: 18px; color: #111827; margin: 28px 0 12px; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }}
  .kpi {{ background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; }}
  .kpi-value {{ font-size: 28px; font-weight: 700; color: #111827; }}
  .kpi-label {{ font-size: 12px; color: #6b7280; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; padding: 8px; border-bottom: 2px solid #d1d5db;
       font-size: 12px; color: #6b7280; text-transform: uppercase; }}
  .footer {{ margin-top: 48px; padding-top: 16px; border-top: 1px solid #e5e7eb;
            font-size: 11px; color: #9ca3af; text-align: center; }}
  @media print {{ body {{ padding: 20px; }} }}
</style>
</head>
<body>
  <div class="header">
    <div class="logo">Brand Brain</div>
    <div class="period">Relatorio: {period_label}</div>
  </div>

  <div class="kpi-grid">
    <div class="kpi">
      <div class="kpi-value">{total_followers_delta:+,}</div>
      <div class="kpi-label">Seguidores (delta)</div>
    </div>
    <div class="kpi">
      <div class="kpi-value">{total_impressions:,}</div>
      <div class="kpi-label">Impressoes</div>
    </div>
    <div class="kpi">
      <div class="kpi-value">{total_engagements:,}</div>
      <div class="kpi-label">Engajamentos (likes+comments+shares)</div>
    </div>
    <div class="kpi">
      <div class="kpi-value">{engagement_rate}%</div>
      <div class="kpi-label">Taxa de Engajamento</div>
    </div>
  </div>

  <h2>Metricas por Plataforma</h2>
  <table>
    <thead>
      <tr>
        <th>Plataforma</th>
        <th style="text-align:right;">Seg. Delta</th>
        <th style="text-align:right;">Impressoes</th>
        <th style="text-align:right;">Engajamentos</th>
        <th style="text-align:right;">Cliques</th>
        <th style="text-align:right;">Taxa Eng.</th>
      </tr>
    </thead>
    <tbody>{provider_rows if provider_rows else '<tr><td colspan="6" style="padding:12px;text-align:center;color:#9ca3af;">Sem dados de metricas no periodo</td></tr>'}</tbody>
  </table>

  <h2>Conteudos no Periodo</h2>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
    <div>
      <h3 style="font-size:14px;color:#6b7280;margin-bottom:8px;">Por Status</h3>
      <table>
        <thead><tr><th>Status</th><th style="text-align:right;">Qtde</th></tr></thead>
        <tbody>{status_rows if status_rows else '<tr><td colspan="2" style="padding:8px;text-align:center;color:#9ca3af;">Nenhum conteudo</td></tr>'}</tbody>
      </table>
    </div>
    <div>
      <h3 style="font-size:14px;color:#6b7280;margin-bottom:8px;">Por Plataforma</h3>
      <table>
        <thead><tr><th>Plataforma</th><th style="text-align:right;">Qtde</th></tr></thead>
        <tbody>{platform_rows if platform_rows else '<tr><td colspan="2" style="padding:8px;text-align:center;color:#9ca3af;">Nenhum conteudo</td></tr>'}</tbody>
      </table>
    </div>
  </div>

  <div class="footer">
    Gerado automaticamente pelo Brand Brain em {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC
  </div>
</body>
</html>"""

    return html


def generate_report_pdf(
    db: Session,
    org_id: str,
    cc_id: Optional[str],
    date_from: date,
    date_to: date,
    report_type: str = "metrics_overview",
) -> bytes:
    """Generate PDF report. Falls back to HTML if weasyprint not available."""
    html = generate_report_html(db, org_id, cc_id, date_from, date_to, report_type)

    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html).write_pdf()
        return pdf_bytes
    except ImportError:
        logger.warning("weasyprint not installed, falling back to HTML-as-bytes")
        return html.encode("utf-8")
