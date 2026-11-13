# src/more_rules.py
"""Адреса, даты рождения, ники в мессенджерах, номера автомобилей."""

import re

from src.extra_rules import FinalSession

_CAP = r"[А-ЯЁӘІҢҒҮҰҚӨҺA-Z][а-яёәіңғүұқөһa-z]+"

# «ул. Абая 150, кв. 12», «проспект Назарбаева 5».
ADDRESS_RE = re.compile(
    r"(?P<pre>(?<!\w)(?i:ул\.|улица|ул|проспект|пр-т|мкр\.|микрорайон|"
    r"переулок|пер\.|бульвар|б-р)[ ]*)"
    rf"(?P<value>{_CAP}(?:[ ]{_CAP}){{0,2}}"
    r"(?:,?[ ]*(?:д\.?[ ]*)?\d+[а-яa-z]?(?:/\d+)?)?"
    r"(?:,[ ]*(?i:кв\.|оф\.|квартира|офис)[ ]*\d+)?)"
)

_MONTHS = (r"(?:январ|феврал|март|апрел|ма[яй]|июн|июл|август|"
           r"сентябр|октябр|ноябр|декабр)\w*")

# «Дата рождения: 12.05.1990», «родился 12 мая 1990».
DOB_RE = re.compile(
    r"(?P<pre>(?<!\w)(?i:дата[ ]+рождения|д\.[ ]?р\.|родил(?:ся|ась)|born)"
    r"[ ]*[:—–-]?[ ]*)"
    rf"(?P<value>\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{2,4}}|"
    rf"\d{{1,2}}[ ](?i:{_MONTHS})[ ]\d{{4}})"
)

# Ники: @username (не трогает email: перед @ нет буквы).
HANDLE_RE = re.compile(r"(?<![\w@.])@[A-Za-z][A-Za-z0-9_]{3,31}(?![\w@])")

# Номера автомобилей РК: 123ABC02, 123 AB 02.
PLATE_RE = re.compile(r"(?<![\w-])\d{3}[ ]?[A-Z]{2,3}[ ]?\d{2}(?![\w-])")
_NOT_PLATE = {"USD", "EUR", "KZT", "RUB", "GBP", "CNY", "TRY"}


def _plate_ok(value):
    return re.sub(r"[^A-Z]", "", value) not in _NOT_PLATE


class UltimateSession(FinalSession):
    def mask(self, text):
        text = self._sub("ADDRESS", ADDRESS_RE, text)
        text = self._sub("DOB", DOB_RE, text)
        text = self._sub("HANDLE", HANDLE_RE, text)
        text = self._sub("PLATE", PLATE_RE, text, _plate_ok)
        return super().mask(text)
