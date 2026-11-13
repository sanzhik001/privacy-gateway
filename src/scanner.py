# src/scanner.py
"""Сканер документов: что найдено, где, насколько опасно."""

import re
from collections import defaultdict

from src.hybrid import HybridSession
from src.lexicon import BLOCK_RE
from src.masker import MARKER_RE

CRITICAL = {"PASSWORD", "API_KEY", "CARD", "IBAN", "ACCOUNT", "DOCUMENT",
            "TAX_ID"}
HIGH = {"NAME", "PHONE", "EMAIL", "ADDRESS", "DOB", "IP", "USERNAME"}
RISK_ORDER = ["critical", "high", "medium"]
RISK_LABELS = {"critical": "🔴 Критичный", "high": "🟠 Высокий",
               "medium": "🟡 Средний"}

KIND_LABELS = {
    "NAME": "ФИО / имя", "PHONE": "Телефон", "EMAIL": "Email",
    "CARD": "Банковская карта", "PASSWORD": "Пароль",
    "API_KEY": "Ключ / токен", "TAX_ID": "ИИН/БИН", "BANK": "Банк",
    "ORG": "Организация", "EMPLOYEES": "Число сотрудников",
    "POSITION": "Должность", "IBAN": "IBAN", "ACCOUNT": "Счёт",
    "MONEY": "Сумма", "KEYWORD": "Ключевое слово", "IP": "IP-адрес",
    "DOCUMENT": "Документ личности", "ID": "Идентификатор",
    "USERNAME": "Логин", "ADDRESS": "Адрес", "DOB": "Дата рождения",
    "HANDLE": "Ник", "PLATE": "Номер авто",
}

# ИИН и БИН оба состоят из 12 цифр. Отличить их по самому числу я не берусь,
# поэтому смотрим на слово перед числом.
_BIN_BEFORE = re.compile(r"(?i)(?<!\w)(бин|bin)\W*$")
_IIN_BEFORE = re.compile(r"(?i)(?<!\w)(иин|iin)\W*$")


def risk_of(kind):
    if kind in CRITICAL:
        return "critical"
    if kind in HIGH:
        return "high"
    return "medium"


def _tax_label(before):
    if _BIN_BEFORE.search(before):
        return "БИН"
    if _IIN_BEFORE.search(before):
        return "ИИН"
    return "ИИН/БИН"


def preview(value):
    v = value.strip()
    if len(v) <= 4:
        return "*" * len(v)
    return v[:2] + "*" * min(len(v) - 3, 8) + v[-1]


def scan_text(text, extra=None):
    """extra: необязательный словарь {"NAME": [...], "ORG": [...]} от Ollama.
    Номера строк приблизительные: они считаются по очищенному тексту."""
    session = HybridSession(extra)
    masked = session.mask(text)

    counts = defaultdict(int)
    lines_of = defaultdict(set)
    first_pos = {}
    pos = 0
    for n, line in enumerate(masked.split("\n"), 1):
        for m in MARKER_RE.finditer(line):
            mk = m.group(0)
            counts[mk] += 1
            lines_of[mk].add(n)
            first_pos.setdefault(mk, pos + m.start())
        pos += len(line) + 1

    findings = []
    for marker, value in session.mapping.items():
        if counts[marker] == 0:
            continue
        kind = MARKER_RE.fullmatch(marker).group(1)
        label = KIND_LABELS.get(kind, kind)
        if kind == "TAX_ID":
            start = first_pos[marker]
            label = _tax_label(masked[max(0, start - 12):start])
        findings.append({
            "marker": marker, "kind": kind, "label": label,
            "risk": risk_of(kind), "value": value,
            "count": counts[marker], "lines": sorted(lines_of[marker]),
        })
    order = {r: i for i, r in enumerate(RISK_ORDER)}
    findings.sort(key=lambda f: (order[f["risk"]], f["kind"], f["marker"]))

    summary = {r: 0 for r in RISK_ORDER}
    for f in findings:
        summary[f["risk"]] += 1

    phrases = []
    if BLOCK_RE:
        phrases = sorted({m.group(0).lower() for m in BLOCK_RE.finditer(text)})

    return {"findings": findings, "masked": masked, "summary": summary,
            "blocked_phrases": phrases, "chars": len(text)}


def report_rows(result, full=False):
    rows = []
    for f in result["findings"]:
        shown = f["value"] if full else preview(f["value"])
        lines = ", ".join(map(str, f["lines"][:10]))
        if len(f["lines"]) > 10:
            lines += " …"
        rows.append({"Риск": RISK_LABELS[f["risk"]], "Тип": f["label"],
                     "Значение": shown, "Вхождений": f["count"],
                     "Строки": lines})
    return rows
