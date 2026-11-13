"""Один безопасный запрос к OpenAI. Ключ из .env, данные искусственные."""

from dotenv import load_dotenv

from src.llm_client import get_provider

load_dotenv()

try:
    provider = get_provider("openai")
    print("Модель:", provider.model)
    print("Ответ:", provider.generate("Скажи привет одним словом."))
except RuntimeError as e:
    print("Ошибка:", e)
