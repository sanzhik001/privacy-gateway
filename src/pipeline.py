# src/pipeline.py
"""Конвейер: политика -> (Ollama) -> маскирование -> исходящая проверка ->
модель -> входящая проверка -> восстановление."""

import re
from collections import Counter

from src.guard import check_response
from src.hybrid import HybridSession
from src.lexicon import has_blocked_words
from src.masker import MARKER_RE

_DATE_RE = re.compile(r"\d{4}-\d{1,2}-\d{1,2}|\d{1,2}-\d{1,2}-\d{4}")


def _count_types(mapping):
    kinds = []
    for marker in mapping:
        m = MARKER_RE.fullmatch(marker)
        if m:
            kinds.append(m.group(1))
    return dict(Counter(kinds))


def _has_unknown_number(masked):
    """Строгий режим: остались ли числа от 6 цифр, которые мы не узнали."""
    rest = MARKER_RE.sub("", masked)
    rest = _DATE_RE.sub("", rest)
    return bool(re.search(r"\d{6,}", rest))


def process_message(user_text, provider, audit=None, strict=False,
                    detector=None):
    """Возвращает словарь со статусом. В нём нет таблицы соответствий.

    audit: необязательный AuditLog (пишет только статус и типы находок).
    strict: блокировать запрос, если остались неопознанные числа.
    detector: None или словарь:
        {
            "model": "qwen3.5:4b",
            "required": True,
            "mask_locations": False
        }
        Ollama ищет имена, организации и локации.
        Если required=True и Ollama недоступна — запрос блокируется.
        mask_locations=True включает маскирование городов.
    """

    def finish(result):
        if audit is not None:
            audit.write(
                result["status"],
                provider.name,
                result["found"],
                result["kinds"],
            )
        return result

    # Политика: запрещённые фразы блокируют запрос целиком.
    if has_blocked_words(user_text):
        return finish({
            "status": "blocked_outbound",
            "found": {},
            "kinds": ["POLICY"],
            "masked": None,
            "answer": None,
        })

    extra = None
    if detector is not None:
        try:
            model = detector.get("model")
            if not model:
                raise RuntimeError("Модель Ollama не выбрана")
            from src.ollama_detector import find_entities
            extra = find_entities(user_text, model)
        except Exception:
            if detector.get("required", True):
                return finish({
                    "status": "blocked_outbound",
                    "found": {},
                    "kinds": ["DETECTOR_DOWN"],
                    "masked": None,
                    "answer": None,
                })
            extra = None

    mask_locations = False
    if detector is not None:
        mask_locations = bool(detector.get("mask_locations", False))

    session = HybridSession(extra, mask_locations=mask_locations)
    masked = session.mask(user_text)
    found = _count_types(session.mapping)

    # Исходящая проверка: в запросе не должно остаться оригиналов.
    leaks = check_response(masked, session.mapping)
    if leaks:
        return finish({
            "status": "blocked_outbound",
            "found": found,
            "kinds": sorted({k for k, _ in leaks}),
            "masked": None,
            "answer": None,
        })

    if strict and _has_unknown_number(masked):
        return finish({
            "status": "blocked_outbound",
            "found": found,
            "kinds": ["UNKNOWN_NUMBER"],
            "masked": None,
            "answer": None,
        })

    try:
        answer = provider.generate(masked)
        if not isinstance(answer, str):
            raise RuntimeError("Ошибка провайдера: пустой ответ")
    except Exception as e:
        error = (
            str(e) if isinstance(e, RuntimeError)
            else "Ошибка провайдера: " + type(e).__name__
        )
        return finish({
            "status": "provider_error",
            "found": found,
            "kinds": [],
            "masked": masked,
            "answer": None,
            "error": error,
        })

    # Входящая проверка: ответ модели не должен содержать утечек.
    findings = check_response(answer, session.mapping)
    if findings:
        return finish({
            "status": "blocked_inbound",
            "found": found,
            "kinds": sorted({k for k, _ in findings}),
            "masked": masked,
            "answer": None,
        })

    return finish({
        "status": "ok",
        "found": found,
        "kinds": [],
        "masked": masked,
        "answer": session.unmask(answer),
    })
