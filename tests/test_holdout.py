import pytest

from src.extra_rules import FinalSession


def mask(text):
    return FinalSession().mask(text)


def test_name_variant_with_surname_without_trigger():
    m = mask("Подготовь краткое резюме: Санджар Оразов, студент 4-го курса")
    assert "Санджар" not in m
    assert "Оразов" not in m


def test_full_name_is_one_marker():
    m = mask("Меня зовут Айгерим Нурлановна Сейтова.")
    assert m.count("[NAME_") == 1


def test_latin_company_after_word():
    m = mask("проходил практику в компании Q-SPACE, работал с документацией")
    assert "Q-SPACE" not in m


@pytest.mark.parametrize("value", [
    "EMP-4821", "TICKET-59381", "DEMO-2026-194",
    "CUST-92817", "CASE-7742", "KZ-DEMO-004812",
])
def test_internal_ids_masked(value):
    assert value not in mask(f"номер {value} в системе")


def test_username_masked():
    assert "demo_user" not in mask('DB_USER="demo_user"')


def test_russian_token_never_restored():
    s = FinalSession()
    masked = s.mask("тестовый токен — DEMO_TOKEN_88XZ")
    assert "DEMO_TOKEN_88XZ" not in masked
    assert "DEMO_TOKEN_88XZ" not in s.unmask(masked)


def test_tech_terms_untouched():
    text = "Используем AES-256-GCM, SHA-256 и UTF-8"
    assert mask(text) == text


def test_ids_restored_exactly():
    text = "Заявка TICKET-59381 по клиенту"
    s = FinalSession()
    assert s.unmask(s.mask(text)) == text

def test_two_digit_markers_are_not_corrupted():
    s = FinalSession()
    text = "; ".join(f'api_key="k{i:02d}abcd"' for i in range(12))
    masked = s.mask(text)
    assert "[ID_" not in masked
    assert masked.count("[API_KEY_") == 12