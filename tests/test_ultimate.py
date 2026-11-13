import pytest

from src.llm_client import LLMProvider
from src.more_rules import UltimateSession
from src.names_db import NAMES
from src.pipeline import process_message


class Spy(LLMProvider):
    name = "spy"

    def __init__(self):
        self.received = []

    def generate(self, masked_text):
        self.received.append(masked_text)
        return "Ок"


def mask(text):
    return UltimateSession().mask(text)


def test_names_base_is_large():
    assert len(NAMES) >= 500


@pytest.mark.parametrize("name", [
    "Бексултан", "Родион", "Нигора", "Серафима", "Ethan", "Charlotte",
])
def test_new_names_are_masked(name):
    assert name not in mask(f"Позвони {name} вечером")


def test_new_name_declension():
    assert "Бексултану" not in mask("Передай Бексултану привет")


def test_address_masked():
    m = mask("Живу на ул. Абая 150, кв. 12")
    assert "Абая" not in m
    assert "150" not in m
    assert "[ADDRESS_1#" in m


def test_address_restored_exactly():
    text = "Живу на проспекте Назарбаева 5, кв. 7"
    s = UltimateSession()
    assert s.unmask(s.mask(text)) == text


def test_birth_date_masked():
    m = mask("Дата рождения: 12.05.1990")
    assert "12.05.1990" not in m
    assert "[DOB_1#" in m


def test_handle_masked():
    m = mask("Мой ник @sanzhar_o в телеграме")
    assert "sanzhar_o" not in m


def test_email_is_not_a_handle():
    m = mask("почта test@example.com")
    assert "[EMAIL_1#" in m
    assert "[HANDLE_" not in m


def test_car_plate_masked():
    assert "123ABC02" not in mask("Машина 123ABC02 у входа")


def test_currency_code_is_not_a_plate():
    assert "[PLATE_" not in mask("стоит 500 USD 10 штук")


def test_org_and_bank_dictionary():
    m = mask("Заказ в Технодом и Sulpak")
    assert "Технодом" not in m
    assert "Sulpak" not in m


def test_medical_keyword():
    assert "инсульт" not in mask("Диагноз: инсульт")


def test_confidential_is_blocked():
    spy = Spy()
    r = process_message("Это конфиденциально, не отправляй", spy)
    assert r["kinds"] == ["POLICY"]
    assert spy.received == []


def test_common_words_untouched():
    text = "Здравствуйте! Вера в будущее, Мир и Роза. Магазин открыт."
    assert mask(text) == text
