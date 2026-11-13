"""Создаёт ключ шифрования журнала и дописывает его в .env."""

from pathlib import Path

from src.audit import generate_key

env = Path(".env")
text = env.read_text() if env.exists() else ""

if "AUDIT_KEY=" in text:
    print("AUDIT_KEY уже есть в .env, ничего не изменено.")
else:
    if text and not text.endswith("\n"):
        text += "\n"
    env.write_text(text + f"AUDIT_KEY={generate_key()}\n")
    print("Ключ записан в .env")