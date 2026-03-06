def check_forbidden_words(text: str, forbidden_words: list[str]) -> list[str]:
    """Check for forbidden words in text and return found words."""
    found_words = []
    text_lower = text.lower()

    for word in forbidden_words:
        if word.lower() in text_lower:
            found_words.append(word)

    return found_words


def check_absolute_promises(text: str) -> list[str]:
    """Check for absolute promise words and return found words."""
    absolute_promise_words = [
        "garantido",
        "100%",
        "milagre",
        "certeza absoluta",
        "infalível",
        "sem risco",
        "prometo",
        "garantia total",
        "absolutamente",
        "nunca falha",
    ]

    found_words = []
    text_lower = text.lower()

    for word in absolute_promise_words:
        if word.lower() in text_lower:
            found_words.append(word)

    return found_words


def validate_content(text: str, influencer) -> dict:
    """Validate content against compliance rules."""
    issues = []

    # Check forbidden words from influencer model
    if hasattr(influencer, "forbidden_words") and influencer.forbidden_words:
        forbidden = check_forbidden_words(text, influencer.forbidden_words)
        if forbidden:
            issues.extend([f"Forbidden word found: {word}" for word in forbidden])

    # Check absolute promises
    absolute_promise_violations = check_absolute_promises(text)
    if absolute_promise_violations:
        issues.extend(
            [f"Absolute promise violation: {word}" for word in absolute_promise_violations]
        )

    return {"valid": len(issues) == 0, "issues": issues}
