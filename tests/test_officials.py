from src.llm_client import LLMProvider
from src.officials import OfficialsSession
from src.pipeline import process_message


class Spy(LLMProvider):
    name = "spy"

    def __init__(self):
        self.received = []

    def generate(self, masked_text):
        self.received.append(masked_text)
        return "Ок"


def test_official_name_and_title_are_masked():
    masked = OfficialsSession().mask("Министр обороны Асхат Нурланов подписал приказ")
    assert "Нурланов" not in masked
    assert "Асхат" not in masked
    assert "Министр" not in masked


def test_military_rank():
    masked = OfficialsSession().mask("Полковник Серик Омаров доложил")
    assert "Омаров" not in masked
    assert "Полковник" not in masked


def test_surname_with_initials():
    masked = OfficialsSession().mask("Приказ подписал Нурланов А.Б. вчера")
    assert "Нурланов" not in masked


def test_initials_before_surname():
    masked = OfficialsSession().mask("Приказ подписал А.Б. Нурланов вчера")
    assert "Нурланов" not in masked


def test_official_restored_exactly():
    text = "Генерал Асхат Нурланов подписал приказ"
    s = OfficialsSession()
    assert s.unmask(s.mask(text)) == text


def test_military_secret_phrase_is_blocked():
    spy = Spy()
    result = process_message("Это военная тайна", spy)
    assert result["kinds"] == ["POLICY"]
    assert spy.received == []


def test_strict_mode_blocks_unknown_number():
    spy = Spy()
    result = process_message("Код объекта 5551234", spy, strict=True)
    assert result["kinds"] == ["UNKNOWN_NUMBER"]
    assert spy.received == []


def test_strict_mode_allows_date():
    result = process_message("Встреча 2026-10-12", Spy(), strict=True)
    assert result["status"] == "ok"