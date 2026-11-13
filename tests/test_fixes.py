import time

import pytest

from src.llm_client import LLMProvider
from src.more_rules import UltimateSession
from src.pipeline import process_message


class Rec(LLMProvider):
    name = "rec"

    def generate(self, masked_text):
        return "Ок"


class Boom(LLMProvider):
    name = "boom"

    def generate(self, masked_text):
        raise ValueError("секретная деталь ошибки")


class Empty(LLMProvider):
    name = "empty"

    def generate(self, masked_text):
        return None


def mask(text):
    return UltimateSession().mask(text)


@pytest.mark.parametrize("text", [
    "сервер 10.0.0.5.", "ip 10.0.0.5, порт 80", "(10.0.0.5)", "адрес: 10.0.0.5!",
])
def test_ip_with_trailing_punctuation_is_masked(text):
    assert "10.0.0.5" not in mask(text)


def test_dotted_version_numbers_are_untouched():
    text = "версия 1.2.3 готова"
    assert mask(text) == text


def test_marker_removal_does_not_create_false_leak():
    r = process_message(
        "работает в компании Q-SPACE Меня зовут Айгерим Сейтова, для отчёта.",
        Rec())
    assert r["status"] == "ok"


@pytest.mark.parametrize("text", [
    "-" * 8000, "a." * 4000 + "@", "1 " * 8000,
], ids=["hyphens", "dots_at", "digits"])
def test_no_pathological_slowdown(text):
    start = time.perf_counter()
    mask(text)
    assert time.perf_counter() - start < 2.0


def test_money_still_masked_after_fix():
    m = mask("сумма 10.000.000, оплата 1 500 000 тенге")
    assert "10.000.000" not in m
    assert "1 500 000" not in m


def test_unexpected_provider_exception_is_reported():
    r = process_message("Привет", Boom())
    assert r["status"] == "provider_error"
    assert "секретная деталь" not in r["error"]


def test_empty_provider_answer_is_reported():
    assert process_message("Привет", Empty())["status"] == "provider_error"
