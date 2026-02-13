# Reddit → Telegram монитор для товаров для сфинксов, корниш-рексов и девон-рексов

Скрипт каждый день:
1. Читает Reddit по заданным сабреддитам и поисковым тегам.
2. Оценивает коммерческий интерес поста по категориям продуктов (одежда, кожа, гигиена, шампуни, лежанки, питание).
3. Отправляет релевантные ссылки в Telegram одним дайджестом.
4. Запоминает уже отправленные посты, чтобы не дублировать.

## 1) Быстрый запуск (рекомендуется)

```bash
bash scripts/setup_and_run.sh once-dry
```

Что делает команда:
- создает `.venv`
- ставит зависимости
- создает `.env` (если его нет)
- запускает проверочный прогон `--once --dry-run` (без отправки в Telegram)

После этого заполните `.env` и запустите рабочий прогон:

```bash
bash scripts/setup_and_run.sh once
```

Для постоянной работы (ежедневно):

```bash
bash scripts/setup_and_run.sh daemon
```

## 2) Ручная установка

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

## 3) Настройка API

### Reddit
1. Откройте: https://www.reddit.com/prefs/apps
2. Нажмите `create app`.
3. Тип: `script`.
4. Заберите:
   - `client_id`
   - `client_secret`

### Telegram
1. Создайте бота через `@BotFather`.
2. Получите `TELEGRAM_BOT_TOKEN`.
3. Добавьте бота в канал/группу.
4. Получите `TELEGRAM_CHAT_ID`:
   - для группы обычно начинается с `-100...`

Заполните `.env` по примеру `.env.example`.

## 4) Проверка перед боем

Проверочный запуск без отправки в Telegram:

```bash
python src/reddit_telegram_monitor.py --once --dry-run
```

Разовый боевой запуск:

```bash
python src/reddit_telegram_monitor.py --once
```

Постоянный режим (по `RUN_TIME_UTC`):

```bash
python src/reddit_telegram_monitor.py
```

## 5) Переменные окружения

Смотрите `.env.example`.
Критично заполнить:
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## 6) Типовые проблемы

### `403 Forbidden` / не ставятся зависимости
Обычно это ограничения сети/прокси. Варианты:
- настроить proxy для pip
- использовать внутренний mirror PyPI
- установить зависимости в среде без ограничений и перенести venv/docker image

### `Отсутствуют обязательные переменные окружения`
Проверьте, что `.env` существует и в нем заполнены ключи.

### Ничего не найдено в дайджесте
Снизьте `MIN_INTEREST_SCORE` (например, до `1`) и/или расширьте `TAGS` и `SUBREDDITS`.

## 7) Тесты

```bash
python -m pytest -q
```
