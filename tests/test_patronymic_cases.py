import pytest

from src.hybrid import HybridSession
from src.names_db import is_patronymic


@pytest.mark.parametrize("word", [
    "Ахметовна", "Ахметовну", "Ахметовне", "Ахметовны",
    "Сагатович", "Сагатовичу", "Сагатовичем", "Ивановичем",
    "Бекжановна", "Нурланқызы", "Серикулы",
])
def test_patronymic_forms(word):
    assert is_patronymic(word)


@pytest.mark.parametrize("word", ["Основной", "Основная", "Головной", "Новичок"])
def test_not_patronymic(word):
    assert not is_patronymic(word)


def test_name_with_patronymic_in_accusative():
    m = HybridSession().mask("Она просит Гульнар Ахметовну перенести встречу.")
    assert "Гульнар" not in m
    assert "Ахметовну" not in m


def test_ordinary_sentence_untouched():
    text = "Основной вопрос решён. Головной офис открыт."
    assert HybridSession().mask(text) == text
