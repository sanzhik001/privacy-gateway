
import pytest

from src.masker import MaskingSession, BLOCKED_TYPES, MARKER_RE


@pytest.mark.parametrize(
    "message",
    [
        "пароль: Secret123",
        "пароль системы 1284392",
        "мой пароль — Secret123",
        "password=Secret123",
        "access code: 123456",
    ],
)
def test_password_is_masked(message):
    session = MaskingSession()
    masked = session.mask(message)

    assert masked != message
    assert any(
        marker_type in BLOCKED_TYPES
        for marker_type in (
            match.group(1)
            for match in MARKER_RE.finditer(masked)
        )
    )


def test_password_is_never_restored():
    session = MaskingSession()
    masked = session.mask("пароль системы 1284392")

    restored = session.unmask(masked)

    assert "1284392" not in restored
    assert "[удалено системом]" in restored
