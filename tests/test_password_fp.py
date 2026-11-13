import pytest

from src.masker import MaskingSession


@pytest.mark.parametrize("text", [
    "Забыл пароль и не могу войти.",
    "Нужен пароль для входа",
    "Сбросить пароль от почты",
])
def test_ordinary_phrases_are_untouched(text):
    assert MaskingSession().mask(text) == text


@pytest.mark.parametrize("text, secret", [
    ("пароль qwerty", "qwerty"),
    ("мой пароль 123456", "123456"),
    ("пароль: Secret123", "Secret123"),
    ('password="Fake Pass"', "Fake Pass"),
])
def test_real_passwords_still_masked(text, secret):
    assert secret not in MaskingSession().mask(text)
