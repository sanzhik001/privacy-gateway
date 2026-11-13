import pytest

from src.masker import MaskingSession


@pytest.mark.parametrize("text", [
    "Встреча 2026-10-12",
    "срок 12-10-2026",
    "в 2026-10-12 12:30",
    "дата 2026-10-12, сумма 110000",
])
def test_dates_are_not_masked_as_phones(text):
    assert MaskingSession().mask(text) == text


@pytest.mark.parametrize("phone", [
    "+7 701 234 56 78",
    "770755671783",
    "8 (701) 234-56-78",
])
def test_real_phones_are_still_masked(phone):
    masked = MaskingSession().mask(f"звоните {phone}")
    assert "[PHONE_1#" in masked