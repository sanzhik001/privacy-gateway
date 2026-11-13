from src.masker import MaskingSession
from src.names_db import NAMES


def test_dictionary_is_loaded():
    assert len(NAMES) >= 200


def test_known_name_without_trigger():
    masked = MaskingSession().mask("Позвони Айгерим вечером")
    assert "Айгерим" not in masked


def test_russian_declension():
    masked = MaskingSession().mask("Передай Асхату привет")
    assert "Асхату" not in masked


def test_kazakh_declension():
    masked = MaskingSession().mask("Это ноутбук Санжардың")
    assert "Санжардың" not in masked


def test_surname_next_to_name_is_one_marker():
    masked = MaskingSession().mask("Позвони Асхат Нурланов вечером")
    assert "Асхат" not in masked
    assert "Нурланов" not in masked
    assert masked.count("[NAME_") == 1


def test_patronymic_alone():
    masked = MaskingSession().mask("Привет, Иванович!")
    assert "Иванович" not in masked


def test_english_name():
    masked = MaskingSession().mask("Call John tomorrow")
    assert "John" not in masked


def test_common_words_are_untouched():
    text = "Здравствуйте! Вера в будущее, Мир и Роза. Магазин открыт."
    assert MaskingSession().mask(text) == text


def test_restore_declined_name_exactly():
    text = "Передай Асхату привет"
    s = MaskingSession()
    assert s.unmask(s.mask(text)) == text