from src.extended import ExtendedSession, iin_check_digit
from src.llm_client import LLMProvider
from src.names_db import NAMES
from src.pipeline import process_message


def make_iban(bban="125KZT5004100100"):
    number = "".join(str(int(c, 36)) for c in bban + "KZ00")
    check = 98 - int(number) % 97
    return f"KZ{check:02d}{bban}"


def make_iin(prefix="90010130"):
    for n in range(1000):
        first11 = prefix + f"{n:03d}"
        digit = iin_check_digit(first11)
        if digit is not None:
            return first11 + str(digit)


class SpyProvider(LLMProvider):
    name = "spy"

    def __init__(self):
        self.received = []

    def generate(self, masked_text):
        self.received.append(masked_text)
        return "Ок"


def test_valid_iban_masked_and_not_restored():
    iban = make_iban()
    s = ExtendedSession()
    masked = s.mask(f"перевод на {iban} срочно")
    assert iban not in masked
    assert "[IBAN_1#" in masked
    restored = s.unmask(masked)
    assert iban not in restored
    assert "[удалено системом]" in restored


def test_invalid_iban_is_not_masked_as_iban():
    bad = "KZ00" + make_iban()[4:]
    masked = ExtendedSession().mask(f"код {bad}")
    assert "[IBAN_" not in masked


def test_iin_without_trigger_is_masked():
    iin = make_iin()
    masked = ExtendedSession().mask(f"номер {iin} проверьте")
    assert iin not in masked
    assert "[TAX_ID_1#" in masked


def test_phone_with_12_digits_is_still_masked():
    masked = ExtendedSession().mask("звоните 770755671783")
    assert "770755671783" not in masked


def test_account_is_masked_and_not_restored():
    s = ExtendedSession()
    masked = s.mask("счёт 1234567890123456")
    assert "1234567890123456" not in masked
    assert "[ACCOUNT_1#" in masked
    assert "1234567890123456" not in s.unmask(masked)


def test_org_dictionary():
    masked = ExtendedSession().mask("Мы работаем с Казатомпром и Google")
    assert "Казатомпром" not in masked
    assert "Google" not in masked


def test_org_restored_exactly():
    text = "Договор с КазМунайГаз подписан"
    s = ExtendedSession()
    assert s.unmask(s.mask(text)) == text


def test_keyword_is_masked():
    masked = ExtendedSession().mask("Запускаем Проект Феникс завтра")
    assert "Феникс" not in masked
    assert "[KEYWORD_1#" in masked


def test_block_words_stop_the_request():
    spy = SpyProvider()
    result = process_message("Это строго конфиденциально", spy)
    assert result["status"] == "blocked_outbound"
    assert result["kinds"] == ["POLICY"]
    assert spy.received == []


def test_clean_text_is_untouched():
    text = "Отчёт по финансам за квартал"
    assert ExtendedSession().mask(text) == text


def test_extra_names_are_loaded():
    assert "ильдар" in NAMES
    assert "adam" in NAMES