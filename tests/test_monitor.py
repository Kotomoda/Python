from src.reddit_telegram_monitor import format_digest, score_post, validate_required_env


def test_score_post_detects_multiple_categories():
    text = "My sphynx has dry skin and hates cold weather after bath"
    score, categories = score_post(text)
    assert score >= 3
    assert "Уход за кожей" in categories
    assert "Одежда и утепление" in categories
    assert "Купание и шампуни" in categories


def test_format_digest_contains_links_and_categories():
    message = format_digest(
        [
            {
                "title": "Need moisturizer for sphynx",
                "url": "https://reddit.com/r/Sphynx/post",
                "subreddit": "Sphynx",
                "score": 2,
                "matched_categories": ["Уход за кожей", "Корм и витамины"],
            }
        ]
    )
    assert "Need moisturizer for sphynx" in message
    assert "https://reddit.com/r/Sphynx/post" in message
    assert "Уход за кожей" in message


def test_validate_required_env_detects_missing(monkeypatch):
    for env_name in (
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    ):
        monkeypatch.delenv(env_name, raising=False)

    missing = validate_required_env()

    assert set(missing) == {
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    }
