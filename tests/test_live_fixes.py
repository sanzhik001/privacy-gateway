from src.extra_rules import FinalSession
from src.hybrid import HybridSession


def test_unknown_first_name_before_patronymic():
    m = FinalSession().mask("Добрый день, Гульнар Ахметовна!")
    assert "Гульнар" not in m
    assert "Ахметовна" not in m


def test_full_name_from_ollama_is_masked():
    text = "Письмо прислала Шырын Тоқа вчера."
    m = HybridSession({"NAME": ["Шырын Тоқа"]}).mask(text)
    assert "Шырын" not in m
    assert "Тоқа" not in m


def test_restore_is_exact():
    text = "Добрый день, Гульнар Ахметовна!"
    s = FinalSession()
    assert s.unmask(s.mask(text)) == text
