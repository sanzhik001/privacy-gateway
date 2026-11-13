# src/officials.py
"""Должностные лица: звания и должности + имя, фамилия с инициалами."""

import re

from src.extended import ExtendedSession
from src.masker import _UP, _LOW, _WORD

_TITLES = (
    r"вице-министр\w*|замминистр\w*|министр\w*|маршал\w*|адмирал\w*|"
    r"генерал\w*|подполковник\w*|полковник\w*|майор\w*|капитан\w*|"
    r"лейтенант\w*|председател\w*|аким\w*|президент\w*|премьер\w*|"
    r"депутат\w*|сенатор\w*|прокурор\w*|посол\w*|ректор\w*|"
    r"директор\w*|замдиректор\w*|начальник\w*|руководител\w*|"
    r"командующ\w*|командир\w*"
)

# Должность + до трёх слов в нижнем регистре («министр обороны») + имя.
OFFICIAL_RE = re.compile(
    rf"(?P<pre>(?<!\w)(?i:{_TITLES})(?:[ ]+[{_LOW}]+){{0,3}}[ ]+)"
    rf"(?P<value>{_WORD}(?:[ ]+{_WORD}){{0,2}})"
)

# «Нурланов А.Б.» и «А.Б. Нурланов».
_INIT = rf"[{_UP}]\.[ ]?[{_UP}]\."
SURNAME_INIT_RE = re.compile(rf"(?<!\w){_WORD}[ ]+{_INIT}")
INIT_SURNAME_RE = re.compile(rf"(?<!\w){_INIT}[ ]?{_WORD}")

# Сама должность тоже маскируется.
TITLE_RE = re.compile(rf"(?<!\w)(?i:{_TITLES})(?!\w)")


class OfficialsSession(ExtendedSession):
    def mask(self, text):
        text = self._sub("NAME", OFFICIAL_RE, text)
        text = self._sub("NAME", SURNAME_INIT_RE, text)
        text = self._sub("NAME", INIT_SURNAME_RE, text)
        text = self._sub("POSITION", TITLE_RE, text)
        return super().mask(text)