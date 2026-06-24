# Kwork Monitor

Полу-автоматический мониторинг биржи заказов Kwork по теме дизайна карточек маркетплейсов и AI-генерации изображений.

Раз в 15 минут (GitHub Actions, бесплатно):
1. `monitor.py` — без авторизации читает `kwork.ru/projects` (категория "Дизайн" + поиск по ключевым словам), отсеивает уже виденные заказы (`seen.json`)
2. `draft.py` — отдаёт каждого кандидата Claude (через Pro-подписку, `CLAUDE_CODE_OAUTH_TOKEN`) на финальную проверку релевантности и написание черновика отклика
3. `notify.py` — присылает в Telegram заголовок, бюджет, ссылку на заказ и черновик отклика

**Отклик на Kwork отправляется только человеком вручную** — бот не пишет и не нажимает ничего на стороне Kwork, только уведомляет.

## Секреты репозитория (Settings → Secrets and variables → Actions)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `CLAUDE_CODE_OAUTH_TOKEN` (генерируется локально командой `claude setup-token`)

## Локальный запуск
```
pip install -r requirements.txt
python -m playwright install chromium
python monitor.py > candidates.json
python draft.py < candidates.json > drafted.json
python notify.py < drafted.json
```
