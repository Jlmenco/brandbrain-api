from worker.publisher import publish_content, PublishResult


def test_publish_linkedin(content_item):
    content_item.provider_target = "linkedin"
    result = publish_content(content_item)
    assert isinstance(result, PublishResult)
    assert result.success is True
    assert result.provider_post_id != ""
    assert "linkedin" in result.provider_post_url


def test_publish_instagram(content_item):
    content_item.provider_target = "instagram"
    result = publish_content(content_item)
    assert result.success is True
    assert "instagram" in result.provider_post_url


def test_publish_facebook(content_item):
    content_item.provider_target = "facebook"
    result = publish_content(content_item)
    assert result.success is True
    assert "facebook" in result.provider_post_url


def test_publish_x(content_item):
    content_item.provider_target = "x"
    result = publish_content(content_item)
    assert result.success is True


def test_publish_tiktok(content_item):
    content_item.provider_target = "tiktok"
    result = publish_content(content_item)
    assert result.success is True


def test_publish_unknown_provider(content_item):
    content_item.provider_target = "unknown_provider"
    result = publish_content(content_item)
    assert result.success is True
    assert result.provider_post_id.startswith("mock_")
