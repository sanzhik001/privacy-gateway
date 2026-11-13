from src.hybrid import HybridSession
from src.masker import MaskingSession


def test_almaty_is_not_a_name():
    text = "Встреча в Алматы"
    assert MaskingSession().mask(text) == text


def test_real_name_almat_is_still_masked():
    assert "Алмат" not in MaskingSession().mask("Позвони Алмат вечером")


def test_place_returned_by_ollama_is_ignored():
    text = "Встреча в Алматы"
    assert HybridSession({"NAME": ["Алматы"]}).mask(text) == text
