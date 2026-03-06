from sqlmodel import Session, select
from app.models.content import MacroContent, ContentItem
from app.models.influencer import Influencer


def redistribute_macro(
    db: Session,
    macro_content: MacroContent,
    target_cc_ids: list,
    provider_targets: list,
    ai_gateway=None,
) -> list:
    """Redistribute a macro content to target cost centers and providers."""
    created_content_ids = []

    for target_cc_id in target_cc_ids:
        # Get the influencer for this cost center
        influencer = db.exec(
            select(Influencer).where(Influencer.cost_center_id == target_cc_id)
        ).first()

        if not influencer:
            continue

        for provider_target in provider_targets:
            # Create a new ContentItem as draft
            adapted_text = f"[AI-ADAPTED] {macro_content.content_raw}"

            content_item = ContentItem(
                cost_center_id=target_cc_id,
                influencer_id=influencer.id,
                status="draft",
                source_macro_id=macro_content.id,
                text=adapted_text,
                provider_target=provider_target,
            )

            db.add(content_item)
            db.flush()
            created_content_ids.append(content_item.id)

    db.commit()
    return created_content_ids
