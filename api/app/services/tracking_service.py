import shortuuid
from sqlmodel import Session
from app.models.tracking import TrackingLink


def generate_slug() -> str:
    """Generate a short unique slug."""
    return shortuuid.uuid()[:8]


def build_utm(provider: str, campaign_name: str, content_item_id: str = "") -> dict:
    """Build UTM parameters for tracking."""
    return {
        "utm_source": provider,
        "utm_medium": "social",
        "utm_campaign": campaign_name,
        "utm_content": str(content_item_id),
    }


def create_short_link(
    db: Session,
    cost_center_id: str,
    destination_url: str,
    content_item_id: str = None,
    campaign_name: str = "",
) -> TrackingLink:
    """Create a short tracking link."""
    slug = generate_slug()
    utm_params = build_utm("social", campaign_name, content_item_id or "")

    tracking_link = TrackingLink(
        slug=slug,
        cost_center_id=cost_center_id,
        destination_url=destination_url,
        content_item_id=content_item_id,
        utm=utm_params,
    )

    db.add(tracking_link)
    db.commit()
    db.refresh(tracking_link)
    return tracking_link
