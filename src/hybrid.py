"""Гибридная сессия: правила + имена и организации, найденные Ollama."""

import re
from pathlib import Path

from src.lexicon import build_regex
from src.more_rules import UltimateSession
from src.names_db import AMBIGUOUS, ENDINGS, NOT_NAMES, is_surname_like

WORD_RE = re.compile(
    r"(?<!\w)[A-Za-zА-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+(?!\w)"
)


def _in_text(value, text):
    """Проверяет точное совпадение отдельного слова."""
    return bool(
        re.search(
            r"(?<!\w)" + re.escape(value) + r"(?!\w)",
            text,
            re.IGNORECASE,
        )
    )


def _find_surface_form(value, text):
    """
    Находит исходную форму фамилии в тексте.
    Например:
    модель вернула 'Нурланов',
    в тексте находится 'Нурланову'.
    Возвращает только реальный фрагмент исходного текста.
    """
    exact = re.search(r"(?<!\w)" + re.escape(value) + r"(?!\w)", text,
                      re.IGNORECASE)
    if exact:
        return exact.group(0)

    base = value.lower()
    for match in WORD_RE.finditer(text):
        token = match.group(0)
        token_lower = token.lower()
        if not token_lower.startswith(base):
            continue
        suffix = token_lower[len(base):]
        if suffix in ENDINGS and is_surname_like(token):
            return token
    return None


_PUBLIC_ORGS_FILE = (Path(__file__).resolve().parent.parent
                     / "data" / "public_orgs.txt")


def _load_public_orgs():
    if not _PUBLIC_ORGS_FILE.exists():
        return []
    return [ln.strip().lower()
            for ln in _PUBLIC_ORGS_FILE.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")]


PUBLIC_ORGS = _load_public_orgs()


def _is_public_org(value):
    """Госорганы (Министерство, Национальный банк) не персональные данные."""
    v = value.lower()
    return any(v.startswith(p) for p in PUBLIC_ORGS)


class HybridSession(UltimateSession):
    def __init__(self, extra=None, mask_locations: bool = False):
        super().__init__()
        self._extra = extra or {}
        self._extra_markers = []
        self.mask_locations = mask_locations

    def _mask_name_parts(self, text):
        """Части найденных ФИО и их падежные формы:
        «Жансерик Оспанов» ... «Жансерик», «Тлеуову», «Бекарысом»."""
        parts = set()
        for marker, value in list(self.mapping.items()):
            if not marker.startswith("[NAME_"):
                continue
            for w in value.split():
                if (len(w) >= 3 and w[0].isupper()
                        and w.lower() not in NOT_NAMES
                        and w.lower() not in AMBIGUOUS):
                    parts.add(w)
        if not parts:
            return text
        suffix = "|".join(re.escape(e)
                          for e in sorted(ENDINGS, key=len, reverse=True))

        def repl(m):
            word = m.group(0)
            if word.lower() in NOT_NAMES:
                return word
            return self._marker_for("NAME", word)

        for w in sorted(parts, key=len, reverse=True):
            rx = re.compile(r"(?<![\w\[#])" + re.escape(w)
                            + r"(?:" + suffix + r")?(?!\w)")
            text = rx.sub(repl, text)
        return text

    def mask(self, text):
        # --- Имена от Ollama ---
        for value in self._extra.get("NAME", []):
            if value.lower() in AMBIGUOUS or value.lower() in NOT_NAMES:
                continue
            original = _find_surface_form(value, text)
            if original is None:
                continue
            self._extra_markers.append(
                self._marker_for("NAME", original)
            )

        # --- Организации от Ollama ---
        orgs = {
            org
            for org in self._extra.get("ORG", [])
            if _in_text(org, text) and not _is_public_org(org)
        }
        if orgs:
            rx = build_regex(orgs)
            if rx:
                text = self._sub("ORG", rx, text)

        # --- Локации от Ollama (опционально) ---
        if self.mask_locations:
            locations = {
                loc
                for loc in self._extra.get("LOCATION", [])
                if _in_text(loc, text)
            }
            if locations:
                rx = build_regex(locations)
                if rx:
                    text = self._sub("LOCATION", rx, text)

        masked = super().mask(text)
        masked = self._mask_name_parts(masked)

        # Убираем из mapping имена, которые не удалось замаскировать.
        for marker in set(self._extra_markers):
            if marker not in masked:
                self.mapping.pop(marker, None)

        return masked
