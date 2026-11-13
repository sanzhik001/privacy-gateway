import pytest

from src.masker import MaskingSession


@pytest.mark.parametrize("card", [
    "4111 1111 1111 1111",
    "4111-1111-1111-1111",
    "4111111111111111",
    "5555 5555 5555 4444",
])
def test_valid_cards_are_masked(card):
    masked = MaskingSession().mask(f"моя карта {card}, спасибо")
    assert "[CARD_1#" in masked
    assert "4111" not in masked
    assert "5555" not in masked


def test_card_is_never_restored():
    s = MaskingSession()
    s.mask("карта 4111 1111 1111 1111")
    marker = list(s.mapping)[0]
    restored = s.unmask(f"Списание с {marker}")
    assert "4111" not in restored
    assert "[удалено системом]" in restored


def test_same_card_different_format_same_marker():
    s = MaskingSession()
    s.mask("4111 1111 1111 1111 и 4111-1111-1111-1111")
    assert len(s.mapping) == 1


def test_non_luhn_number_is_not_card():
    # 16 цифр, но проверку Луна не проходит
    masked = MaskingSession().mask("номер заказа 1234567890123456")
    assert "[CARD_" not in masked