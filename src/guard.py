# src/guard.py
"""Проверка текста на утечки (цензор).

Используется дважды: перед отправкой модели (исходящая проверка)
и после ответа модели (входящая проверка).
"""

from src.masker import (PATTERNS, MARKER_RE, _looks_like_card,
                        _looks_like_phone, _false_password)
from src.names_db import NOT_NAMES


def _is_real(kind, value):
    """Те же проверки, что и при маскировании: даты не телефоны,
    числа без контрольной суммы Луна не карты, «пароль и» не пароль."""
    if kind == "CARD":
        return _looks_like_card(value)
    if kind == "PHONE":
        return _looks_like_phone(value)
    if kind == "PASSWORD":
        return not _false_password(value)
    return True


def check_response(text, mapping):
    """Ищет чувствительные данные в тексте.

    Возвращает список находок. Пустой список = текст чистый.
    """
    findings = []

    stripped = MARKER_RE.sub("§", text)

    for kind, pattern in PATTERNS:
        for match in pattern.finditer(stripped):
            if (kind == "NAME" and "value" in match.re.groupindex
                    and match.group("value").split()[0].lower() in NOT_NAMES):
                continue
            if _is_real(kind, match.group(0)):
                findings.append((kind, match.group(0)))

    for original in mapping.values():
        if original and original in stripped:
            findings.append(("LEAK_FROM_MAPPING", original))

    return findings
