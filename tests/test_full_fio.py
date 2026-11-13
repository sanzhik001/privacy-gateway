from src.extra_rules import FinalSession
from src.hybrid import HybridSession

TEXT = "Мирзахметов Бауыржан Сагатович отсутствует."


def test_fio_surname_first_rules():
    m = FinalSession().mask(TEXT)
    for w in ("Мирзахметов", "Бауыржан", "Сагатович"):
        assert w not in m


def test_fio_from_ollama_when_rules_took_part():
    m = HybridSession({"NAME": ["Мирзахметов Бауыржан Сагатович"]}).mask(TEXT)
    for w in ("Мирзахметов", "Бауыржан", "Сагатович"):
        assert w not in m


def test_fio_restored_exactly():
    s = HybridSession({"NAME": ["Мирзахметов Бауыржан Сагатович"]})
    assert s.unmask(s.mask(TEXT)) == TEXT


def test_patronymic_case_still_works():
    m = FinalSession().mask("Добрый день, Гульнар Ахметовна!")
    assert "Гульнар" not in m
