"""Проверка на реалистичных запросах. Все данные искусственные."""

from src.extended import iin_check_digit
from src.llm_client import LLMProvider
from src.pipeline import process_message


def make_iin(prefix):
    for n in range(1000):
        first11 = prefix + f"{n:03d}"
        d = iin_check_digit(first11)
        if d is not None:
            return first11 + str(d)


def make_iban(bban="125KZT5004100100"):
    number = "".join(str(int(c, 36)) for c in bban + "KZ00")
    return f"KZ{98 - int(number) % 97:02d}{bban}"


class Spy(LLMProvider):
    name = "spy"

    def generate(self, masked_text):
        return "Ок"


IIN1, IIN2, IIN3 = make_iin("90010130"), make_iin("85051250"), make_iin("78030720")
IBAN = make_iban()

# (название, текст, что должно быть скрыто)
CASES = [
    ("HR: предупреждение сотруднику",
     f"Составь предупреждение сотруднику Нурлан Сериков, ИИН {IIN1}, "
     "зарплата 450 000 тенге, за опоздания.",
     ["Нурлан", "Сериков", IIN1, "450 000"]),

    ("Клиент: ответ на жалобу",
     "Напиши ответ клиенту Дана Ахметова (dana.akhmetova@mail.kz), "
     "тел. 8 777 123 45 67, по поводу возврата 25 000 тг",
     ["Дана", "Ахметова", "dana.akhmetova@mail.kz", "777 123 45 67", "25 000"]),

    ("Код: строка подключения и токен",
     'DB_URL = "postgresql://admin:Qwerty2026@10.0.0.5:5432/crm"\n'
     'API_TOKEN = "ghp_" + "abcdefghijklmnopqrstuvwxyz0123456789"',
     ["Qwerty2026", "10.0.0.5", "ghp_" + "abcdefghijklmnopqrstuvwxyz0123456789"]),

    ("Протокол встречи",
     "Присутствовали Асхат Омаров (директор), Айгерим Сейтова (бухгалтер). "
     f"Обсудили кредит в Halyk на 120.000.000 тенге, счёт {IBAN}",
     ["Омаров", "Сейтова", "Halyk", "120.000.000", IBAN]),

    ("Медицина",
     f"У пациента Ерлан Жумабаев диагноз ВИЧ, ИИН {IIN2}, наблюдается у врача",
     ["Жумабаев", "ВИЧ", IIN2]),

    ("Договор",
     f"Договор между ТОО Ромашка (БИН {IIN3}) и ИП Серикбаев Данияр, "
     "адрес: г. Алматы, ул. Абая 150, кв. 12",
     ["Ромашка", IIN3, "Серикбаев", "Абая 150"]),

    ("Документ личности",
     "Удостоверение личности N12345678 выдано МВД РК",
     ["N12345678"]),

    ("Список клиентов",
     "Айгерим;+7 701 111 22 33;aigerim@test.kz\n"
     "Асхат;+7 702 222 33 44;askhat@test.kz",
     ["Айгерим", "701 111 22 33", "aigerim@test.kz",
      "Асхат", "702 222 33 44", "askhat@test.kz"]),

    ("Английский: имя, почта, пароль",
     "My name is John Smith, email john.smith@test.com, password: Hunter2!",
     ["John", "Smith", "john.smith@test.com", "Hunter2!"]),

    ("Чистый запрос (ничего не должно меняться)",
     "Объясни разницу между кредитом и лизингом простыми словами", []),
]

total = safe = 0
for title, text, hide in CASES:
    r = process_message(text, Spy())
    masked = r["masked"]
    if masked is None:
        print(f"[БЛОК ] {title}: запрос не отправлен ({r['kinds']})")
        total += max(len(hide), 1)
        safe += max(len(hide), 1)
        continue
    if not hide:
        ok = masked == text
        total += 1
        safe += ok
        print(f"[{'ОК   ' if ok else 'ИЗМЕН'}] {title}")
        continue
    leaked = [h for h in hide if h in masked]
    total += len(hide)
    safe += len(hide) - len(leaked)
    if leaked:
        print(f"[УТЕЧКА] {title}: не скрыто {leaked}")
    else:
        print(f"[ОК   ] {title}")

print(f"\nПокрытие: скрыто {safe} из {total}")