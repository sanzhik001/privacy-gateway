# src/extra_rules.py
"""Технические секреты, идентификаторы, IP, документы, имена по фамилии.

Эти правила запускаются ДО остальных: IP-адрес не должен стать
«суммой», а токен не должен разбиться на куски.
"""

import re

from src.masker import BLOCKED_TYPES, CAP_SEQ_RE, _ORG_PRE
from src.names_db import is_known_name, is_patronymic, is_surname_like
from src.officials import OfficialsSession, TITLE_RE

BLOCKED_TYPES.update({"DOCUMENT"})

# Пароль внутри адреса: scheme://user:ПАРОЛЬ@host
URL_PASSWORD_RE = re.compile(
    r"(?P<pre>(?<!\w)[A-Za-z][A-Za-z0-9+.\-]{0,20}://[^\s:/@]+:)"
    r"(?P<value>[^\s@/]+)(?=@)"
)

# Токены известных форматов (GitHub, AWS, Google, Slack).
TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:gh[pousr]_[A-Za-z0-9]{20,}|"
    r"github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|"
    r"AIza[0-9A-Za-z_\-]{30,}|xox[baprs]-[A-Za-z0-9\-]{10,})"
)

# Имя = значение: SECRET_KEY=..., api_token: ..., DB_PASSWORD=...
# (?!\[) не даёт обернуть уже готовый маркер ещё одним маркером.
KEY_VALUE_RE = re.compile(
    r"(?P<pre>(?<![\w-])(?i:[\w-]{0,40}(?:secret|token|api[_-]?key|passwd|pwd|"
    r"password)[\w-]{0,40})[ ]*[:=][ ]*[\"']?)"
    r"(?P<value>(?!\[)[^\s\"',;]{4,})"
)

# По-русски: «токен — DEMO_TOKEN_88XZ». Значение обязано содержать цифру,
# чтобы не ловить обычные фразы вроде «ключ — это важно».
TOKEN_WORD_RE = re.compile(
    r"(?P<pre>(?<!\w)(?i:токен\w*|ключ\w*(?:[ ]+доступа)?|token)"
    r"[ ]*[:=—–-][ ]*[\"']?)"
    r"(?P<value>(?=[^\s\"',;]*\d)(?!\[)[^\s\"',;]{4,})"
)

# Логины: DB_USER="demo_user", логин: ivanov
USER_RE = re.compile(
    r"(?P<pre>(?<![\w-])(?i:[\w-]{0,40}(?:user(?:name)?|login)|логин)"
    r"[ ]*[:=—–][ ]*[\"']?)"
    r"(?P<value>(?!\[)[^\s\"',;]{3,})"
)

IP_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?!\d|\.\d)")

# Документы личности: «удостоверение личности N12345678», «паспорт 123456789».
DOCUMENT_RE = re.compile(
    r"(?P<pre>(?<!\w)(?i:удостоверени\w*[ ]+личности|паспорт\w*|passport)"
    r"[ ]*[:№#]?[ ]*)"
    r"(?P<value>[A-Z]{0,2}\d{7,10})(?!\d)"
)

# Идентификаторы вида EMP-4821, TICKET-59381, DEMO-2026-194, KZ-DEMO-004812.
# Перед совпадением не должно быть «[»: так мы не заденем свои маркеры.
ID_RE = re.compile(
    r"(?<![\w\[-])[A-Z][A-Z0-9]{1,9}(?:[-_][A-Z0-9]{2,12}){1,3}(?![\w-])"
)
# Технические термины, которые не являются идентификаторами.
_TECH = {"SHA", "ISO", "UTF", "RFC", "AES", "RSA", "TLS", "SSL", "MD",
         "HTTP", "IEEE", "DES", "GOST"}

# Латинские названия компаний после «компании», «ТОО» и т. п.
ORG_LATIN_RE = re.compile(
    rf"(?P<pre>{_ORG_PRE})"
    r"(?P<value>[«\"]?[A-Z][A-Za-z0-9&]*(?:-[A-Za-z0-9&]+)*"
    r"(?:[ ][A-Z][A-Za-z0-9&]*(?:-[A-Za-z0-9&]+)*){0,2}[»\"]?)"
)


def _ip_ok(value):
    return all(int(p) <= 255 for p in value.split("."))


def _id_ok(value):
    first = re.split(r"[-_]", value)[0]
    return any(c.isdigit() for c in value) and first not in _TECH


class FinalSession(OfficialsSession):
    def _mask_surname_pairs(self, text):
        """Слово с заглавной буквы + слово с окончанием фамилии
        («Санджар Оразов»). Должность перед фамилией не затрагивается."""

        def handle(m):
            words = m.group(0).split(" ")
            flags = [False] * len(words)
            hit = False
            for i in range(1, len(words)):
                if is_surname_like(words[i]) or is_patronymic(words[i]):
                    hit = True
                    flags[i] = True
                    if not TITLE_RE.fullmatch(words[i - 1]):
                        flags[i - 1] = True
            if not hit:
                return m.group(0)
            for i, w in enumerate(words):
                if is_known_name(w) or is_patronymic(w):
                    flags[i] = True
            for i, w in enumerate(words):
                if not flags[i] and is_surname_like(w) and (
                        (i > 0 and flags[i - 1])
                        or (i + 1 < len(words) and flags[i + 1])):
                    flags[i] = True

            out, run = [], []
            for w, f in zip(words, flags):
                if f:
                    run.append(w)
                else:
                    if run:
                        out.append(self._marker_for("NAME", " ".join(run)))
                        run = []
                    out.append(w)
            if run:
                out.append(self._marker_for("NAME", " ".join(run)))
            return " ".join(out)

        return CAP_SEQ_RE.sub(handle, text)

    def mask(self, text):
        text = self._sub("PASSWORD", URL_PASSWORD_RE, text)
        text = self._sub("API_KEY", TOKEN_RE, text)
        text = self._sub("API_KEY", KEY_VALUE_RE, text)
        text = self._sub("API_KEY", TOKEN_WORD_RE, text)
        text = self._sub("USERNAME", USER_RE, text)
        text = self._sub("IP", IP_RE, text, _ip_ok)
        text = self._sub("DOCUMENT", DOCUMENT_RE, text)
        text = self._sub("ID", ID_RE, text, _id_ok)
        text = self._sub("ORG", ORG_LATIN_RE, text)
        text = self._mask_surname_pairs(text)
        return super().mask(text)