# src/lexicon.py
"""Словари: организации, маскируемые слова, запрещённые фразы.

Читаются из data/<имя>.txt и data/extra/<имя>_*.txt.
Формат: один термин на строку, # = комментарий.
"""

import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_terms(stem):
    files = [DATA_DIR / f"{stem}.txt"]
    extra = DATA_DIR / "extra"
    if extra.is_dir():
        files += sorted(extra.glob(f"{stem}_*.txt"))
    terms = set()
    for f in files:
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and len(line) >= 3:
                terms.add(line)
    return terms


def build_regex(terms):
    """Один шаблон на весь словарь: длинные термины первыми,
    границы слов, регистр не важен, пробел = любое число пробелов."""
    if not terms:
        return None
    ordered = sorted(terms, key=len, reverse=True)
    body = "|".join(re.escape(t).replace("\\ ", "[ ]+") for t in ordered)
    return re.compile(rf"(?<!\w)(?:{body})(?!\w)", re.IGNORECASE)


ORG_DICT_RE = build_regex(load_terms("orgs"))
KEYWORD_RE = build_regex(load_terms("mask_words"))
BLOCK_RE = build_regex(load_terms("block_words"))


def has_blocked_words(text):
    """True, если в тексте есть запрещённая фраза."""
    return bool(BLOCK_RE and BLOCK_RE.search(text))