"""Зависает ли маскирование на «злых» входах (каждый случай в процессе)."""

import subprocess
import sys
import time

LIMIT = 15

CASES = {
    "обычный текст 200 КБ": lambda: "Объясни разницу между кредитом и лизингом. " * 4700,
    "цифры через пробел": lambda: "1 " * 30000,
    "плюс и семёрки": lambda: "+" + "7" * 50000,
    "только пробелы": lambda: " " * 100000,
    "одно длинное слово": lambda: "а" * 200000,
    "слова с заглавной": lambda: "Аа " * 20000,
    "точки перед @": lambda: "a." * 30000 + "@",
    "слово пароль подряд": lambda: "пароль " * 10000,
    "дефисы": lambda: "-" * 50000,
    "скобки": lambda: "(" * 50000,
    "идентификаторы": lambda: "AB-12 " * 10000,
    "запятые и цифры": lambda: "12," * 30000,
    "адреса": lambda: "ул. Абая " * 8000,
}


def run_one(name):
    from src.llm_client import LLMProvider
    from src.pipeline import process_message

    class Quiet(LLMProvider):
        name = "quiet"

        def generate(self, masked_text):
            return "ok"

    text = CASES[name]()
    start = time.time()
    process_message(text, Quiet())
    print(f"{time.time() - start:.2f}")


if len(sys.argv) > 1:
    run_one(sys.argv[1])
    sys.exit()

for name in CASES:
    try:
        out = subprocess.run([sys.executable, __file__, name],
                             capture_output=True, text=True, timeout=LIMIT)
    except subprocess.TimeoutExpired:
        print(f"[ЗАВИСАНИЕ >{LIMIT}с] {name}")
        continue
    if out.returncode != 0:
        lines = out.stderr.strip().splitlines()
        print(f"[ОШИБКА] {name}: {lines[-1] if lines else ''}")
        continue
    sec = float(out.stdout.strip().splitlines()[-1])
    flag = "МЕДЛЕННО" if sec > 2 else "ок"
    print(f"[{flag:8}] {name}: {sec:.2f} с")
