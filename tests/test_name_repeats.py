from src.masker import MaskingSession


def test_all_repeats_of_name_are_masked():
    masked = MaskingSession().mask(
        "Меня зовут Айгерим. Айгерим любит чай. Позвони Айгерим.")
    assert "Айгерим" not in masked
    assert masked.count("[NAME_1#") == 3


def test_repeat_is_case_insensitive():
    masked = MaskingSession().mask("Меня зовут Айгерим. АЙГЕРИМ тоже тут.")
    assert "АЙГЕРИМ" not in masked
    assert "Айгерим" not in masked


def test_longer_word_is_not_touched():
    masked = MaskingSession().mask("Меня зовут Али. Алифка и Али друзья.")
    assert "Алифка" in masked
    assert masked.count("[NAME_1#") == 2


def test_text_is_restored_exactly():
    text = "Меня зовут Айгерим. Айгерим любит чай."
    s = MaskingSession()
    assert s.unmask(s.mask(text)) == text


def test_latin_name_repeats_are_masked_and_restored():
    text = "My name is Bekzat. Bekzat likes tea."
    s = MaskingSession()
    masked = s.mask(text)
    assert "Bekzat" not in masked
    assert masked.count("[NAME_1#") == 2
    assert s.unmask(masked) == text


def test_unknown_name_without_trigger_is_still_untouched():
    # Граница метода: этого имени нет в словаре и нет фразы-триггера.
    text = "Зхырбек любит чай."
    assert MaskingSession().mask(text) == text