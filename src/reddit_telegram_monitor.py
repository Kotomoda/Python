"""Daily Reddit monitor for cat-product lead discovery and Telegram digest delivery."""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

if TYPE_CHECKING:
    import praw


@dataclass
class MonitorConfig:
    reddit_client_id: str
    reddit_client_secret: str
    reddit_user_agent: str
    telegram_bot_token: str
    telegram_chat_id: str
    subreddits: list[str]
    tags: list[str]
    run_time_utc: str
    state_file: Path
    max_posts_per_tag: int
    min_interest_score: int


PRODUCT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Одежда и утепление": (
        "cold",
        "freezing",
        "sweater",
        "hoodie",
        "jacket",
        "clothes",
        "одежд",
        "кофта",
        "мерз",
        "холод",
    ),
    "Уход за кожей": (
        "skin",
        "dry",
        "acne",
        "rash",
        "moisturizer",
        "lotion",
        "шелуш",
        "кожа",
        "крем",
        "прыщ",
    ),
    "Гигиена ушей/глаз": (
        "ear wax",
        "ears",
        "eye discharge",
        "tear stain",
        "уш",
        "глаз",
        "выделен",
    ),
    "Купание и шампуни": (
        "bath",
        "shampoo",
        "wash",
        "odor",
        "smell",
        "купан",
        "шампун",
        "запах",
    ),
    "Лежанки и пледы": (
        "blanket",
        "bed",
        "heated",
        "sleep",
        "лежанк",
        "плед",
        "грелк",
    ),
    "Корм и витамины": (
        "food",
        "diet",
        "allergy",
        "treat",
        "supplement",
        "корм",
        "аллерг",
        "витамин",
    ),
}


REQUIRED_ENV_VARS = (
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
)


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        return

    load_dotenv()


def validate_required_env() -> list[str]:
    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
    return missing


def load_config() -> MonitorConfig:
    load_dotenv_if_available()

    missing = validate_required_env()
    if missing:
        names = ", ".join(missing)
        raise ValueError(
            f"Отсутствуют обязательные переменные окружения: {names}. "
            "Скопируйте .env.example в .env и заполните значения."
        )

    state_file = Path(os.getenv("STATE_FILE", ".monitor_state.json"))
    return MonitorConfig(
        reddit_client_id=os.environ["REDDIT_CLIENT_ID"],
        reddit_client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        reddit_user_agent=os.getenv("REDDIT_USER_AGENT", "cat-product-monitor/1.0"),
        telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        telegram_chat_id=os.environ["TELEGRAM_CHAT_ID"],
        subreddits=parse_csv(
            os.getenv("SUBREDDITS", "Sphynx,CornishRex,DevonRex,cats,catadvice")
        ),
        tags=parse_csv(
            os.getenv(
                "TAGS",
                "sphynx,sphynx cat,cornish rex,devon rex,hairless cat,cat skincare",
            )
        ),
        run_time_utc=os.getenv("RUN_TIME_UTC", "08:00"),
        state_file=state_file,
        max_posts_per_tag=int(os.getenv("MAX_POSTS_PER_TAG", "25")),
        min_interest_score=int(os.getenv("MIN_INTEREST_SCORE", "2")),
    )


def load_state(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    return set(payload.get("sent_post_ids", []))


def save_state(path: Path, sent_post_ids: Iterable[str]) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump({"sent_post_ids": sorted(set(sent_post_ids))}, file, ensure_ascii=False, indent=2)


def build_reddit_client(config: MonitorConfig) -> Any:
    import praw

    return praw.Reddit(
        client_id=config.reddit_client_id,
        client_secret=config.reddit_client_secret,
        user_agent=config.reddit_user_agent,
    )


def score_post(text: str) -> tuple[int, list[str]]:
    lowered = text.lower()
    matched_categories: list[str] = []

    for category, keywords in PRODUCT_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            matched_categories.append(category)

    return len(matched_categories), matched_categories


def fetch_candidate_posts(reddit: Any, config: MonitorConfig) -> list[dict]:
    newest_allowed = datetime.now(timezone.utc) - timedelta(hours=24)
    results_by_id: dict[str, dict] = {}

    for subreddit_name in config.subreddits:
        subreddit = reddit.subreddit(subreddit_name)
        for tag in config.tags:
            for post in subreddit.search(
                query=tag,
                sort="new",
                syntax="lucene",
                time_filter="day",
                limit=config.max_posts_per_tag,
            ):
                created_utc = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                if created_utc < newest_allowed:
                    continue

                text_blob = f"{post.title}\n\n{post.selftext}"
                score, matched_categories = score_post(text_blob)
                if score < config.min_interest_score:
                    continue

                results_by_id[post.id] = {
                    "id": post.id,
                    "title": post.title,
                    "url": f"https://reddit.com{post.permalink}",
                    "subreddit": subreddit_name,
                    "score": score,
                    "matched_categories": matched_categories,
                    "created_utc": created_utc.isoformat(),
                }

    sorted_items = sorted(
        results_by_id.values(),
        key=lambda item: (item["score"], item["created_utc"]),
        reverse=True,
    )
    return sorted_items


def format_digest(posts: list[dict]) -> str:
    header = "🐾 *Ежедневная подборка Reddit для бренда товаров для сфинксов/рексов*\n"
    lines = [header]

    for idx, post in enumerate(posts, start=1):
        categories = ", ".join(post["matched_categories"])
        lines.append(
            f"{idx}. [{post['title']}]({post['url']})\n"
            f"   Сабреддит: r/{post['subreddit']}\n"
            f"   Интерес: {post['score']} | Категории: {categories}"
        )

    if not posts:
        lines.append("За последние 24 часа релевантных постов не найдено.")

    return "\n\n".join(lines)


def send_to_telegram(config: MonitorConfig, message: str) -> None:
    import requests

    endpoint = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
    response = requests.post(
        endpoint,
        json={
            "chat_id": config.telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    response.raise_for_status()


def run_once(config: MonitorConfig, dry_run: bool = False) -> None:
    reddit = build_reddit_client(config)
    sent_post_ids = load_state(config.state_file)

    candidates = fetch_candidate_posts(reddit, config)
    fresh_candidates = [post for post in candidates if post["id"] not in sent_post_ids]

    digest_text = format_digest(fresh_candidates)

    if dry_run:
        print(digest_text)
        return

    send_to_telegram(config, digest_text)

    updated_ids = sent_post_ids | {post["id"] for post in fresh_candidates}
    save_state(config.state_file, updated_ids)


def run_scheduler(config: MonitorConfig, dry_run: bool = False) -> None:
    schedule = __import__("schedule")

    schedule.every().day.at(config.run_time_utc).do(run_once, config, dry_run)
    mode = "DRY-RUN" if dry_run else "send-to-telegram"
    print(f"Scheduler started ({mode}). Daily digest at {config.run_time_utc} UTC")

    while True:
        schedule.run_pending()
        time.sleep(20)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reddit -> Telegram daily lead monitor")
    parser.add_argument("--once", action="store_true", help="Run once now and exit")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not send to Telegram, print digest to stdout",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        config = load_config()
        if args.once:
            run_once(config, dry_run=args.dry_run)
        else:
            run_scheduler(config, dry_run=args.dry_run)
    except Exception as exc:
        print(f"Ошибка запуска: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
