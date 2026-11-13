# src/names_db.py
"""База имён: словарь + склонения + отчества + фамилии.

Словарь читается из data/names.txt и всех файлов data/extra/*.txt.
Формат: имена через запятую или по одному в строке, # = комментарий.
"""

import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Имена, совпадающие с обычными словами: из словаря исключаются,
# чтобы не портить обычный текст. После фраз «меня зовут» они всё
# равно находятся.
AMBIGUOUS = {
    "вера", "надежда", "любовь", "роза", "мир", "мира", "май",
    "роман", "лев", "марк", "дана",
}

# Падежные окончания (русские и казахские). Длинные проверяются первыми.
ENDINGS = sorted([
    "ами", "ями", "ом", "ем", "ём", "ой", "ей", "ою", "ею", "ам", "ям",
    "ах", "ях", "а", "я", "у", "ю", "е", "ы", "и",
    "ның", "нің", "дың", "дің", "тың", "тің", "мен", "бен", "пен",
    "нан", "нен", "дан", "ден", "тан", "тен",
    "ға", "ге", "қа", "ке", "ды", "ді", "ты", "ті", "ны", "ні",
    "да", "де", "та", "те",
], key=len, reverse=True)

_NAME_CHARS = re.compile(r"[a-zа-яёәіңғүұқөһ-]+")

PATRONYMIC_RE = re.compile(
    r".{2,}(?:(?:ович|евич|ьич)(?:а|у|ем|ом|е)?"
    r"|(?:овн|евн|ичн|иничн)(?:а|ы|е|у)"
    r"|(?:ұлы|қызы|улы|кызы))"
)
SURNAME_RE = re.compile(
    r".{2,}(?:ов|ев|ёв|ин|ын|ова|ева|ёва|ина|ына|ский|ская|цкий|цкая|"
    r"ского|ской|енко|ук|юк|ян|дзе)(?:а|у|ым|ом|е|ой|ых)?"
)


def _read(path):
    found = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for part in line.split(","):
            name = part.strip().lower()
            if len(name) >= 3 and _NAME_CHARS.fullmatch(name):
                found.add(name)
    return found


def _load():
    names = set()
    files = [DATA_DIR / "names.txt"]
    extra = DATA_DIR / "extra"
    if extra.is_dir():
        files += sorted(extra.glob("names*.txt"))
    for f in files:
        if f.exists():
            names |= _read(f)
    return names - AMBIGUOUS


NAMES = _load()


def _load_not_names():
    """Слова, которые похожи на имена, но именами не являются
    (города и т. п.): data/not_names.txt."""
    path = DATA_DIR / "not_names.txt"
    if not path.exists():
        return set()
    return {ln.strip().lower()
            for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")}


NOT_NAMES = _load_not_names()


def _known_word(w):
    if w in NOT_NAMES:
        return False
    if w in NAMES:
        return True
    for e in ENDINGS:
        if w.endswith(e):
            stem = w[:-len(e)]
            if len(stem) >= 3:
                for v in ("", "а", "я", "ь", "й"):
                    if stem + v in NAMES:
                        return True
    return False


def is_known_name(word):
    w = word.lower()
    if "-" in w:
        return all(_known_word(p) for p in w.split("-") if p)
    return _known_word(w)


def is_patronymic(word):
    return bool(PATRONYMIC_RE.fullmatch(word.lower()))


def is_surname_like(word):
    return bool(SURNAME_RE.fullmatch(word.lower()))

_PATRONYMIC_OBLIQUE_RE = re.compile(r".{2,}(?:овн|евн|ичн)(?:ой|ою)")


def is_patronymic_oblique(word):
    """«Сериковной»: только рядом с именем, иначе это может быть «Основной»."""
    return bool(_PATRONYMIC_OBLIQUE_RE.fullmatch(word.lower()))
