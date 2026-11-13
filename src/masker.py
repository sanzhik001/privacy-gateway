# src/masker.py
"""Модуль маскирования и восстановления чувствительных данных.

Один запрос пользователя = один объект MaskingSession.
Таблица соответствий «маркер -> исходное значение» хранится
только в оперативной памяти и исчезает после завершения запроса.
"""

import re
import secrets

from src.names_db import NOT_NAMES, is_known_name, is_patronymic, is_surname_like, is_patronymic_oblique

# ---------------------------------------------------------------------------
# Шаблоны детекции (регулярные выражения)
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r'(?<![\w.+-])[\w.+-]{1,64}@[\w.-]{1,255}\.[a-zA-Z]{2,24}\b')
PHONE_RE = re.compile(r'(?<!\w)(?:\+?\d[\d\s()\-]{7,}\d)(?!\w)')

# Банковские карты: 13-19 цифр, можно с пробелами или дефисами между ними.
CARD_RE = re.compile(r'(?<![\w-])\d(?:[ -]?\d){12,18}(?![\w-])')

# Кандидат в телефоны, который на самом деле является датой.
DATE_START_RE = re.compile(r'^(?:\d{4}-\d{1,2}-\d{1,2}|\d{1,2}-\d{1,2}-\d{4})')
MIN_PHONE_DIGITS = 10

PASSWORD_RE = re.compile(
    r'(?i)\b(?:пароль|password|passwd|passcode|'
    r'код\s+доступа|access\s+code)\b'
    r'\s*(?:системы|аккаунта|учётной\s+записи|'
    r'учетной\s+записи|system|account)?'
    r'\s*(?:[:=—–-]\s*|\s+(?:это|равен|is)\s+|\s+)'
    r'(?:"[^"\n]{1,200}"|\'[^\'\n]{1,200}\'|[^\s,;.!?]+)'
)
API_KEY_RE = re.compile(r'\bsk-[A-Za-z0-9]{20,}\b')

# БИН / ИИН: 12 цифр после слова-триггера.
TAX_ID_RE = re.compile(
    r'(?P<pre>(?<!\w)(?i:бин|иин|bin|iin)[ ]*[:=№#—–-]?[ ]*)'
    r'(?P<value>\d{12})(?!\d)'
)

# Количество сотрудников: «кол-во сотрудников 110000», «сотрудников: 1 200».
EMPLOYEES_RE = re.compile(
    r'(?P<pre>(?<!\w)(?i:(?:кол-?во|количество|число|штат)[ ]+)?'
    r'(?i:сотрудников|работников|персонала|employees)[ ]*[:=—–-]?[ ]*)'
    r'(?P<value>\d+(?:[ ]\d{3})*)'
)

# Банки (словарь).
BANK_RE = re.compile(
    r'(?<!\w)(?:'
    r'kaspi|каспи|halyk|халык|jusan|жусан|'
    r'forte[ ]?bank|форте[ ]?банк|freedom[ ](?:bank|finance)|фридом|'
    r'bereke|береке|сбербанк|сбер|tinkoff|тинькофф|'
    r'альфа[- ]?банк|alfa[- ]?bank|home[ ]credit|хоум[ ]кредит|'
    r'втб|vtb|центркредит|centercredit|eurasian[ ]bank|евразийский[ ]банк|'
    r'нурбанк|nurbank|ситибанк|citibank|банк[ ]рбк|bank[ ]rbk'
    r')(?!\w)',
    re.IGNORECASE,
)

# Организации: после «ТОО», «АО», «компании», «корпорации» и т. п.
_UP = "А-ЯЁӘІҢҒҮҰҚӨҺA-Z"
_LOW = "а-яёәіңғүұқөһa-z"
_WORD = rf"[{_UP}][{_LOW}]+(?:-[{_UP}][{_LOW}]+)?"
_ORG_PRE = (
    r'(?:(?<!\w)(?:ТОО|АО|ООО|ЗАО|ИП)[ ]+|'
    r'(?<!\w)(?i:компани[яиюей]|корпораци[яиюей]|организаци[яиюей]|'
    r'фирм[аыуе]|предприяти[еяю])[ ]+)'
)
ORG_RE = re.compile(
    rf'(?P<pre>{_ORG_PRE})'
    rf'(?P<value>[«"]?{_WORD}(?:[ ]+{_WORD}){{0,2}}[»"]?)'
)

# Должности (словарь основ слов).
POSITION_RE = re.compile(
    r'(?<!\w)(?:директор|бухгалтер|менеджер|программист|разработчик|юрист|'
    r'инженер|аналитик|администратор|начальник|руководител|врач|учител|'
    r'преподавател|специалист|секретар)\w*',
    re.IGNORECASE,
)

# Имена после слов-триггеров.
_NAME_TRIGGERS = (
    r'(?:меня|его|её|ее|вас|тебя)[ ]+зовут|мо[её][ ]+имя|my[ ]+name[ ]+is|'
    r'сотрудник\w*|клиент\w*|директор\w*|менеджер\w*|бухгалтер\w*|'
    r'руководител\w*|начальник\w*'
)
NAME_RE = re.compile(
    rf'(?P<pre>(?<!\w)(?i:{_NAME_TRIGGERS})(?:[ ]*[:—–-][ ]*|[ ]+))'
    rf'(?P<value>{_WORD}(?:[ ]+{_WORD}){{0,2}})'
)

# Последовательность из 1-4 слов с заглавной буквы (для словаря имён).
CAP_SEQ_RE = re.compile(rf'(?<!\w){_WORD}(?:[ ]{_WORD}){{0,3}}(?!\w)')

# Порядок важен: сначала секреты, затем идентификаторы и карты (чтобы они
# не были приняты за телефон), потом остальное. NAME стоит раньше POSITION,
# иначе слово «директор» исчезнет и имя после него не найдётся.
# Словарные имена сюда не входят: их ищет _mask_known_names.
PATTERNS = [
    ("API_KEY", API_KEY_RE),
    ("PASSWORD", PASSWORD_RE),
    ("TAX_ID", TAX_ID_RE),
    ("CARD", CARD_RE),
    ("EMAIL", EMAIL_RE),
    ("PHONE", PHONE_RE),
    ("EMPLOYEES", EMPLOYEES_RE),
    ("BANK", BANK_RE),
    ("ORG", ORG_RE),
    ("NAME", NAME_RE),
    ("POSITION", POSITION_RE),
]

# Типы данных, которые нельзя возвращать в ответ пользователю.
BLOCKED_TYPES = {"PASSWORD", "API_KEY", "CARD"}

# Шаблон «настоящего» маркера: [TYPE_число#6_символов_hex]
MARKER_RE = re.compile(r"\[([A-Z_]+)_(\d+)#([0-9a-f]{6})\]")


def _normalize(kind, value):
    """Приводим значение к единому виду, чтобы одинаковые
    значения в разной записи считались одним и тем же."""
    if kind in ("PHONE", "CARD"):
        return re.sub(r'\D', '', value)   # оставляем только цифры
    return value.lower()


def _luhn_ok(digits):
    """Проверка номера карты по алгоритму Луна."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _looks_like_card(value):
    digits = re.sub(r'\D', '', value)
    return 13 <= len(digits) <= 19 and _luhn_ok(digits)


def _looks_like_phone(value):
    """Вторая проверка кандидата в телефоны: отсеиваем даты
    и слишком короткие числа."""
    if DATE_START_RE.match(value):
        return False
    return len(re.sub(r'\D', '', value)) >= MIN_PHONE_DIGITS


# Слова, которые после слова «пароль» не могут быть самим паролем:
# «забыл пароль и не могу войти», «пароль от почты».
_PW_STOP = {
    "и", "а", "но", "или", "не", "ни", "от", "для", "в", "на", "с", "со",
    "к", "по", "из", "за", "при", "о", "об", "у", "же", "ли", "что", "как",
    "мой", "моя", "мне", "его", "её", "ее", "ваш", "есть", "нет", "был",
    "была", "уже", "тоже", "лучше", "надо", "нужно",
    "and", "or", "the", "for", "of", "to", "in", "on", "my", "your", "a",
    "is", "was", "from", "with",
}


def _false_password(fragment):
    """True, если после слова «пароль» стоит служебное слово,
    а не значение пароля."""
    last = fragment.split()[-1].strip(".,;:!?").lower()
    return last in _PW_STOP


class MaskingSession:
    """Один запрос пользователя = один объект MaskingSession.
    Он хранит таблицу соответствий только в памяти."""

    def __init__(self):
        self.nonce = secrets.token_hex(3)  # случайный код сессии, 6 символов
        self.mapping = {}      # маркер -> исходное значение
        self._seen = {}        # (тип, нормализованное значение) -> маркер
        self._counters = {}    # тип -> сколько маркеров уже выдано

    def _marker_for(self, kind, value):
        """Возвращает маркер для значения: старый, если такое
        значение уже встречалось в этом запросе, иначе новый."""
        key = (kind, _normalize(kind, value))
        if key in self._seen:
            return self._seen[key]

        number = self._counters.get(kind, 0) + 1
        self._counters[kind] = number
        marker = f"[{kind}_{number}#{self.nonce}]"
        self._seen[key] = marker
        self.mapping[marker] = value
        return marker

    def _replace(self, kind, m):
        """Решает, чем заменить найденный фрагмент."""
        if kind == "CARD" and not _looks_like_card(m.group(0)):
            return m.group(0)

        if kind == "PHONE" and not _looks_like_phone(m.group(0)):
            return m.group(0)

        if (kind == "NAME" and "value" in m.re.groupindex
                and m.group("value").split()[0].lower() in NOT_NAMES):
            return m.group(0)

        if kind == "PASSWORD" and _false_password(m.group(0)):
            return m.group(0)

        # Если в шаблоне есть группа value, заменяем только её,
        # а начало фразы (pre) оставляем.
        if "value" in m.re.groupindex:
            return m.group("pre") + self._marker_for(kind, m.group("value"))
        return self._marker_for(kind, m.group(0))

    def _mask_known_names(self, text):
        """Ищет имена по словарю (с учётом склонений), отчества и
        фамилии. Фамилия маскируется только рядом с известным именем."""

        def handle(m):
            words = m.group(0).split(" ")
            base = [is_known_name(w) or is_patronymic(w) for w in words]
            flags = list(base)
            for i, w in enumerate(words):
                if not flags[i] and (is_surname_like(w)
                                     or is_patronymic_oblique(w)):
                    near_prev = i > 0 and base[i - 1]
                    near_next = i + 1 < len(words) and base[i + 1]
                    if near_prev or near_next:
                        flags[i] = True
            if not any(flags):
                return m.group(0)

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

    def _mask_name_repeats(self, text):
        """Заменяет все остальные вхождения уже найденных имён.

        Границы слов: «Али» не трогает «Алифка». Регистр не важен.
        Текст внутри готовых маркеров не меняется.
        """
        lookup = {
            value.lower(): marker
            for marker, value in self.mapping.items()
            if marker.startswith("[NAME_")
        }
        if not lookup:
            return text

        names = sorted(lookup, key=len, reverse=True)
        name_re = re.compile(
            r"(?<!\w)(?:" + "|".join(re.escape(n) for n in names) + r")(?!\w)",
            re.IGNORECASE,
        )

        parts = []
        last = 0
        for mm in MARKER_RE.finditer(text):
            parts.append(name_re.sub(lambda m: lookup[m.group(0).lower()],
                                     text[last:mm.start()]))
            parts.append(mm.group(0))
            last = mm.end()
        parts.append(name_re.sub(lambda m: lookup[m.group(0).lower()],
                                 text[last:]))
        return "".join(parts)

    def mask(self, text):
        """Заменяет чувствительные данные на маркеры."""
        for kind, pattern in PATTERNS:
            text = pattern.sub(
                lambda m, k=kind: self._replace(k, m),
                text,
            )
        text = self._mask_known_names(text)
        return self._mask_name_repeats(text)

    def unmask(self, text):
        """Восстанавливает значения в ответе модели по таблице соответствий.

        Правила безопасности:
        - восстанавливаем ТОЛЬКО маркеры, найденные по MARKER_RE и
          присутствующие в self.mapping этой сессии;
        - чужие/поддельные маркеры не трогаем;
        - пароли, API-ключи и номера карт не возвращаем никогда.
        """
        result = []
        last = 0

        for match in MARKER_RE.finditer(text):
            result.append(text[last:match.start()])
            marker = match.group(0)
            marker_type = match.group(1)

            if marker in self.mapping:
                if marker_type in BLOCKED_TYPES:
                    result.append("[удалено системом]")
                else:
                    result.append(self.mapping[marker])
            else:
                result.append(marker)

            last = match.end()

        result.append(text[last:])
        return "".join(result)


if __name__ == "__main__":
    session = MaskingSession()
    user_text = (
        "Меня зовут Айгерим, телефон +7 701 234 56 78, "
        "почта aigerim@test.kz, пароль: Secret123"
    )
    masked = session.mask(user_text)
    print("Текст для модели:", masked)

    fake_answer = f"Принято, ваш телефон {list(session.mapping)[0]}"
    print("Ответ модели:   ", fake_answer)
    print("Для пользователя:", session.unmask(fake_answer))