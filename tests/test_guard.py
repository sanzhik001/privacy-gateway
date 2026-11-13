from src.masker import MaskingSession
from src.guard import check_response


def test_clean_response_passes():
    session = MaskingSession()
    masked = session.mask("Мой номер +7 701 234 56 78")
    answer = f"Ваш номер {list(session.mapping)[0]} записан."
    assert check_response(answer, session.mapping) == []


def test_leaked_phone_detected():
    session = MaskingSession()
    session.mask("Мой номер +7 701 234 56 78")
    findings = check_response("Ваш номер +7 701 234 56 78", session.mapping)
    assert len(findings) > 0


def test_leaked_original_from_mapping_detected():
    session = MaskingSession()
    session.mask("почта test@example.com")
    findings = check_response("test@example.com подтверждена", session.mapping)
    assert len(findings) > 0