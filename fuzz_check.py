"""Случайные тексты из искусственных фрагментов. Все данные вымышленные."""

import random
import re
from collections import defaultdict

from src.guard import check_response
from src.masker import BLOCKED_TYPES, MARKER_RE
from src.more_rules import UltimateSession

TOKEN = "ghp_" + "abcdefghijklmnopqrstuvwxyz0123456789"

FRAGS = [
    ("Меня зовут Айгерим Сейтова", ["Айгерим", "Сейтова"]),
    ("телефон +7 701 234 56 78", ["701 234 56 78"]),
    ("почта test@example.com", ["test@example.com"]),
    ("карта 4111 1111 1111 1111", ["4111"]),
    ("пароль: Secret123", ["Secret123"]),
    ("ТОО Ромашка, БИН 123456789012", ["Ромашка", "123456789012"]),
    ("директор Асхат Нурланов", ["Асхат", "Нурланов"]),
    ("счёт 12928392", ["12928392"]),
    ("сумма 10.000.000 тенге", ["10.000.000"]),
    ("живу на ул. Абая 150, кв. 12", ["Абая"]),
    ("дата рождения: 12.05.1990", ["12.05.1990"]),
    ("ник @aigerim_test", ["aigerim_test"]),
    ("машина 123ABC02", ["123ABC02"]),
    ("заявка TICKET-59381", ["TICKET-59381"]),
    ('DB_USER="demo_user"', ["demo_user"]),
    ("сервер 10.0.0.5", ["10.0.0.5"]),
    (f"токен {TOKEN}", [TOKEN]),
    ("диагноз ВИЧ", ["ВИЧ"]),
    ("позвони Бексултану", ["Бексултану"]),
    ("перевод в Kaspi Bank", ["Kaspi"]),
    ("работает в компании Q-SPACE", ["Q-SPACE"]),
    ("удостоверение личности N12345678", ["12345678"]),
]
FILLERS = ["пожалуйста", "срочно", "завтра", "в понедельник", "для отчёта",
           "это важно", "спасибо", "по проекту", "в офисе"]
SEPS = [" ", ", ", ". ", "; ", "\n"]

rng = random.Random(42)
problems = defaultdict(list)
N = 1500

for _ in range(N):
    parts = rng.sample(FRAGS, rng.randint(2, 5))
    items = [(p[0], p[1]) for p in parts]
    for _ in range(rng.randint(0, 2)):
        items.insert(rng.randint(0, len(items)), (rng.choice(FILLERS), []))
    text = ""
    for i, (frag, _s) in enumerate(items):
        text += frag + (rng.choice(SEPS) if i < len(items) - 1 else ".")
    secrets = [s for _f, ss in items for s in ss]

    session = UltimateSession()
    try:
        masked = session.mask(text)
    except Exception as e:
        problems["исключение"].append((text, type(e).__name__))
        continue

    leaked = [s for s in secrets if s in masked]
    if leaked:
        problems["не скрыто"].append((text, leaked))

    kinds = {MARKER_RE.fullmatch(m).group(1) for m in session.mapping}
    if not kinds & BLOCKED_TYPES and session.unmask(masked) != text:
        problems["потеря при восстановлении"].append((text, ""))

    found = check_response(masked, session.mapping)
    if found:
        problems["ложная блокировка цензором"].append((text, found[:2]))

print(f"Прогнано текстов: {N}")
if not problems:
    print("Проблем не найдено.")
for kind, items in problems.items():
    print(f"\n[{kind}] случаев: {len(items)}")
    for text, detail in items[:5]:
        print("  текст:", re.sub(r"\s+", " ", text)[:200])
        if detail:
            print("  детали:", detail)

from collections import Counter
_c = Counter(s for _t, leaked in problems.get("не скрыто", []) for s in leaked)
print("\nЧаще всего не скрыто:", dict(_c))
