# src/extended.py
"""Расширенная сессия маскирования: IBAN, ИИН/БИН, счета, суммы и словари.

Наследует MaskingSession. Сначала маскируются секреты (пароли, ключи),
затем числовые идентификаторы и словари, потом всё остальное.
"""

import re

from src.masker import MaskingSession, PATTERNS, BLOCKED_TYPES
from src.lexicon import ORG_DICT_RE, KEYWORD_RE

# IBAN и счета, как и карты, пользователю не возвращаются.
BLOCKED_TYPES.update({"IBAN", "ACCOUNT"})

# Казахстанский IBAN: KZ + 2 цифры + 16 символов (всего 20).
IBAN_RE = re.compile(
    r"(?<![A-Za-z0-9])KZ\d{2}(?:[ ]?[A-Z0-9]){16}(?![A-Za-z0-9])",
    re.IGNORECASE,
)

# Счёт: слово-триггер (+ необязательные «этот», «номер») + число от 6 цифр.
ACCOUNT_RE = re.compile(
    r"(?P<pre>(?<!\w)(?i:сч[её]т\w*|р/с|account)"
    r"(?:[ ]+(?i:этот|этого|номер|№|на|в))*[ ]*[:=№#—–-]?[ ]*)"
    r"(?P<value>\d(?:[ ]?\d){5,24})(?!\d)"
)

# Суммы: «10.000.000», «1 500 000 тенге», «$5000», «5000 USD».
_CUR = r"(?i:тенге|тг|₸|руб\w*|₽|usd|eur|доллар\w*|евро|\$|€)"
MONEY_RE = re.compile(
    rf"(?<![\w.,])"
    rf"(?:{_CUR}[ ]?\d[\d .,]{{0,25}}\d|"
    rf"\d{{1,3}}(?:[.,]\d{{3}}){{2,}}(?:[ ]?{_CUR})?|"
    rf"\d[\d ]{{0,25}}\d[ ]?{_CUR})"
    rf"(?![\w])"
)

# ИИН/БИН без слова-триггера: ровно 12 цифр.
IIN_RE = re.compile(r"(?<![\w-])\d{12}(?![\w-])")

_W1 = list(range(1, 12))
_W2 = [3, 4, 5, 6, 7, 8, 9, 10, 11, 1, 2]


def iin_check_digit(first11):
    """Контрольная цифра ИИН/БИН по первым 11 цифрам (None = недопустимо)."""
    d = [int(c) for c in first11]
    s = sum(x * w for x, w in zip(d, _W1)) % 11
    if s == 10:
        s = sum(x * w for x, w in zip(d, _W2)) % 11
        if s == 10:
            return None
    return s


def _iin_ok(value):
    digits = re.sub(r"\D", "", value)
    if len(digits) != 12:
        return False
    return iin_check_digit(digits[:11]) == int(digits[11])


def _iban_ok(value):
    s = re.sub(r"\s", "", value).upper()
    if len(s) != 20 or not s.startswith("KZ"):
        return False
    rearranged = s[4:] + s[:4]
    number = "".join(str(int(ch, 36)) for ch in rearranged)
    return int(number) % 97 == 1


class ExtendedSession(MaskingSession):
    def _sub(self, kind, regex, text, check=None):
        def rep(m):
            if "value" in m.re.groupindex:
                value = m.group("value")
                if check and not check(value):
                    return m.group(0)
                return m.group("pre") + self._marker_for(kind, value)
            if check and not check(m.group(0)):
                return m.group(0)
            return self._marker_for(kind, m.group(0))

        return regex.sub(rep, text)

    def mask(self, text):
        # 1. Секреты первыми, чтобы их цифры не стали «ИИН» или «счётом».
        for kind, pattern in PATTERNS:
            if kind in ("API_KEY", "PASSWORD"):
                text = pattern.sub(
                    lambda m, k=kind: self._replace(k, m), text)

        # 2. Числовые идентификаторы.
        text = self._sub("IBAN", IBAN_RE, text, _iban_ok)
        text = self._sub("ACCOUNT", ACCOUNT_RE, text)
        text = self._sub("TAX_ID", IIN_RE, text, _iin_ok)

        # 3. Суммы и словари.
        text = self._sub("MONEY", MONEY_RE, text)
        if ORG_DICT_RE:
            text = self._sub("ORG", ORG_DICT_RE, text)
        if KEYWORD_RE:
            text = self._sub("KEYWORD", KEYWORD_RE, text)

        # 4. Всё остальное (карты, телефоны, имена и так далее).
        return super().mask(text)