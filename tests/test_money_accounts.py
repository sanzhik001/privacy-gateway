from src.extended import ExtendedSession


def test_short_account_with_words_between():
    masked = ExtendedSession().mask("нужно скинуть на этот счет 12928392")
    assert "12928392" not in masked
    assert "[ACCOUNT_1#" in masked


def test_account_without_yo():
    masked = ExtendedSession().mask("счет 1234567")
    assert "1234567" not in masked


def test_money_with_dots():
    masked = ExtendedSession().mask("сумма выходять за 10.000.000, срочно")
    assert "10.000.000" not in masked


def test_money_with_currency():
    masked = ExtendedSession().mask("оплата 1 500 000 тенге и $5000")
    assert "1 500 000" not in masked
    assert "5000" not in masked


def test_money_is_restored_exactly():
    text = "сумма 10.000.000 на счет 12928392"
    s = ExtendedSession()
    assert s.unmask(s.mask(text)) == text.replace("12928392", "[удалено системом]")


def test_date_and_plain_number_untouched():
    text = "Встреча 2026-10-12, сумма 110000"
    assert ExtendedSession().mask(text) == text