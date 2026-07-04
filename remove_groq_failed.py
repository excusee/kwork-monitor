"""Убирает из seen.json заказы где Groq упал с ошибкой — они перепроверятся в следующем прогоне."""
import json
import re
import sys
from pathlib import Path

log = Path("classify_log.txt").read_text()
failed = re.findall(r"Groq недоступен для (\d+):", log)
if failed:
    seen = json.loads(Path("seen.json").read_text())
    seen = [x for x in seen if x not in failed]
    Path("seen.json").write_text(json.dumps(seen, ensure_ascii=False, indent=2))
    print(f"Убрали из seen.json {len(failed)} ID с ошибкой Groq: {failed}")
