#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-once-dry}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 не найден. Установите Python 3.10+"
  exit 1
fi

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Создан .env из .env.example. Заполните ключи и запустите скрипт снова."
  exit 1
fi

case "$MODE" in
  once-dry)
    python src/reddit_telegram_monitor.py --once --dry-run
    ;;
  once)
    python src/reddit_telegram_monitor.py --once
    ;;
  daemon)
    python src/reddit_telegram_monitor.py
    ;;
  *)
    echo "Неизвестный режим: $MODE"
    echo "Использование: scripts/setup_and_run.sh [once-dry|once|daemon]"
    exit 1
    ;;
esac
