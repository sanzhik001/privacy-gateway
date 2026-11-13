from src.masker import MaskingSession


def test_mask_phone_and_email():
    session = MaskingSession()
    masked = session.mask("Мой телефон +7 701 234 56 78, почта test@example.com")
    assert "+7 701 234 56 78" not in masked
    assert "test@example.com" not in masked
    assert "[PHONE_1#" in masked
    assert "[EMAIL_1#" in masked


def test_repeated_values_get_same_marker():
    session = MaskingSession()
    masked = session.mask("+7 701 234 56 78 и снова +77012345678")
    assert masked.count("[PHONE_1#") == 2
    assert "[PHONE_2#" not in masked


def test_unmasking():
    session = MaskingSession()
    original_text = "Мой номер +7 701 555 11 22"
    masked = session.mask(original_text)
    assert masked != original_text
    marker = list(session.mapping.keys())[0]
    ai_response = f"Ваш номер {marker} записан."
    restored = session.unmask(ai_response)
    assert restored == "Ваш номер +7 701 555 11 22 записан."


def test_fake_marker_protection():
    session = MaskingSession()
    session.mask("Обычный текст")
    fake_response = "Ваш телефон [PHONE_1#abc123]"
    restored = session.unmask(fake_response)
    assert restored == fake_response


def test_secret_is_never_restored():
    session = MaskingSession()
    session.mask("Мой пароль: Secret123")
    password_marker = [m for m in session.mapping if m.startswith("[PASSWORD_")][0]
    restored = session.unmask(f"Ваш секрет: {password_marker}")
    assert "Secret123" not in restored
    assert "[удалено системом]" in restored