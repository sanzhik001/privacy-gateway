"""Privacy Gateway: чат-бот с защитным слоем (Streamlit)."""

import os
import time

import streamlit as st
from dotenv import load_dotenv

from src.audit import AuditLog
from src.llm_client import get_provider
from src.ollama_detector import list_models
from src.pipeline import process_message

load_dotenv()

st.set_page_config(page_title="Privacy Gateway", page_icon="🛡️", layout="wide")

CSS = """
<style>
.pg-hero {background: linear-gradient(135deg,#0f2027 0%,#203a43 50%,#2c5364 100%);
  padding: 22px 28px; border-radius: 16px; color: #fff; margin-bottom: 18px;
  border: 1px solid rgba(255,255,255,.08);}
.pg-hero h1 {margin: 0; font-size: 2rem; color: #fff;}
.pg-hero p {margin: 6px 0 0 0; color: #cfe3ea; font-size: .95rem;}
.pg-badge {display: inline-block; padding: 3px 11px; margin: 2px 5px 2px 0;
  border-radius: 999px; font-size: .78rem; font-weight: 600; color: #fff;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

KINDS = {
    "NAME": ("Имена", "#3b82f6"), "PHONE": ("Телефоны", "#10b981"),
    "EMAIL": ("Email", "#06b6d4"), "CARD": ("Карты", "#ef4444"),
    "PASSWORD": ("Пароли", "#dc2626"), "API_KEY": ("Ключи и токены", "#b91c1c"),
    "TAX_ID": ("ИИН/БИН", "#8b5cf6"), "BANK": ("Банки", "#f59e0b"),
    "ORG": ("Организации", "#f97316"), "EMPLOYEES": ("Штат", "#a855f7"),
    "POSITION": ("Должности", "#64748b"), "IBAN": ("IBAN", "#ef4444"),
    "ACCOUNT": ("Счета", "#ef4444"), "MONEY": ("Суммы", "#eab308"),
    "KEYWORD": ("Ключевые слова", "#14b8a6"), "IP": ("IP", "#6366f1"),
    "DOCUMENT": ("Документы", "#e11d48"), "ID": ("Идентификаторы", "#0ea5e9"),
    "USERNAME": ("Логины", "#84cc16"), "ADDRESS": ("Адреса", "#d946ef"),
    "DOB": ("Даты рождения", "#f43f5e"), "HANDLE": ("Ники", "#22c55e"),
    "PLATE": ("Номера авто", "#78716c"),
}

EXAMPLES = {
    "Письмо работодателю": "Меня зовут Арман Садыков. Мой телефон +7 700 123 45 67, почта arman.test@example.com. Подготовьте письмо с просьбой перенести собеседование",
    "Пароль и карта": "Мой пароль: Secret123, карта 4111 1111 1111 1111",
    "Бизнес": "Директор Асхат Нурланов из ТОО Ромашка, БИН 123456789012, банк Kaspi, сумма 10.000.000 тенге",
    "Адрес и дата": "Айгерим живёт на ул. Абая 150, кв. 12, дата рождения: 12.05.1990, ник @aigerim_test",
    "Код с секретами": 'DB_USER="demo_user", DB_PASSWORD="FakePass-123!", сервер 10.0.0.5',
    "Запрещённая фраза": "Это строго конфиденциально",
    "Дата (не телефон)": "Встреча 2026-10-12, сумма 110000",
}

ss = st.session_state
ss.setdefault("messages", [])
ss.setdefault("stats", {"messages": 0, "masked": 0, "blocked": 0})
ss.setdefault("demo_text", list(EXAMPLES.values())[0])


def get_audit():
    if os.getenv("AUDIT_KEY"):
        os.makedirs("logs", exist_ok=True)
        return AuditLog("logs/audit.enc")
    return None


def badges(found):
    parts = []
    for kind, count in sorted(found.items()):
        label, color = KINDS.get(kind, (kind, "#6b7280"))
        parts.append(f'<span class="pg-badge" style="background:{color}">'
                     f"{label} × {count}</span>")
    return "".join(parts)


def reply_for(result):
    kinds = result.get("kinds", [])
    status = result["status"]
    if status == "ok":
        return result["answer"]
    if "POLICY" in kinds:
        return "⛔ Запрос заблокирован политикой: в тексте запрещённая фраза."
    if "UNKNOWN_NUMBER" in kinds:
        return "⛔ Строгий режим: в тексте остались неопознанные числа."
    if "DETECTOR_DOWN" in kinds:
        return "⛔ Ollama недоступна: запрос не отправлен (включена блокировка)."
    if status == "blocked_outbound":
        return "⛔ Запрос заблокирован: в нём остались исходные данные."
    if status == "blocked_inbound":
        return "⛔ Ответ модели заблокирован цензором."
    err = result.get("error", "Ошибка провайдера")
    if "RateLimitError" in err:
        err += ". Проверь баланс и лимиты API."
    return "⚠️ " + err


def handle(text, provider_name, strict, detector=None):
    try:
        provider = get_provider(provider_name)
    except (RuntimeError, ValueError) as e:
        return {"status": "provider_error", "found": {}, "kinds": [],
                "masked": None, "answer": None, "error": str(e)}
    return process_message(text, provider, audit=get_audit(), strict=strict,
                           detector=detector)


def record(result):
    s = ss.stats
    s["messages"] += 1
    s["masked"] += sum(result.get("found", {}).values())
    if result["status"].startswith("blocked"):
        s["blocked"] += 1


def render_assistant(msg, show_masked):
    st.write(msg["text"])
    if msg.get("badges"):
        st.markdown(msg["badges"], unsafe_allow_html=True)
    if msg.get("masked") and show_masked:
        with st.expander("Что ушло модели"):
            st.code(msg["masked"], language=None)


def queue(text):
    ss.pending = text


def set_demo(text):
    ss.demo_text = text


# Пароль на вход (если задан CHAT_PASSWORD в .env).
password = os.getenv("CHAT_PASSWORD")
if password and not ss.get("auth"):
    st.title("🛡️ Privacy Gateway")
    entered = st.text_input("Пароль доступа", type="password")
    if entered:
        if entered == password:
            ss.auth = True
            st.rerun()
        else:
            st.error("Неверный пароль")
    st.stop()

with st.sidebar:
    st.markdown("## 🛡️ Privacy Gateway")
    mode = st.radio("Раздел", ["💬 Чат", "🔬 Демо", "🔐 Журнал"])
    st.divider()
    provider_name = st.selectbox("Провайдер", ["mock", "openai"])
    if provider_name == "openai":
        st.warning("Реальный вызов API. Модель получает только маркеры. "
                   "Вводи искусственные данные.")
        confirmed = st.checkbox("Понимаю, отправить в облако")
    else:
        st.info("Заглушка: повторяет текст. Это не настоящая модель.")
        confirmed = True
    show_masked = st.checkbox("Показывать, что ушло модели", value=True)
    strict = st.checkbox("Строгий режим", value=False,
                         help="Блокирует запрос, если остались неопознанные числа")
    use_ollama = st.checkbox(
        "🧠 Ollama-детектор (имена и организации)", value=True,
        help="Локальная модель дополняет правила. Работает только на этом компьютере.")
    ollama_model = None
    ollama_required = True
    if use_ollama:
        try:
            _models = list_models()
        except RuntimeError as e:
            _models = []
            st.error(str(e))
        if _models:
            ollama_model = st.selectbox("Модель Ollama", _models)
        ollama_required = st.checkbox(
            "Блокировать запрос, если Ollama недоступна", value=True)
    detector = ({"model": ollama_model, "required": ollama_required}
                if use_ollama else None)
    st.divider()
    st.caption("Статус защиты")
    st.write("🔐 Журнал AES-256-GCM:",
             "включён" if os.getenv("AUDIT_KEY") else "выключен")
    st.write("🧠 Провайдер:", provider_name)
    if st.button("Очистить чат"):
        ss.messages = []
        ss.stats = {"messages": 0, "masked": 0, "blocked": 0}
        st.rerun()

st.markdown(
    '<div class="pg-hero"><h1>🛡️ Privacy Gateway</h1>'
    "<p>Защитный слой между вами и облачной нейросетью: данные маскируются "
    "до отправки и возвращаются только в ваш ответ. Учебный прототип, "
    "вводите только искусственные данные.</p></div>",
    unsafe_allow_html=True,
)
c1, c2, c3 = st.columns(3)
c1.metric("Сообщений", ss.stats["messages"])
c2.metric("Значений скрыто", ss.stats["masked"])
c3.metric("Заблокировано", ss.stats["blocked"])

if mode == "💬 Чат":
    with st.expander("Готовые примеры"):
        cols = st.columns(3)
        for i, (title, text) in enumerate(EXAMPLES.items()):
            cols[i % 3].button(title, key=f"ex_{i}", on_click=queue, args=(text,))

    for msg in ss.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                render_assistant(msg, show_masked)
            else:
                st.write(msg["text"])

    prompt = st.chat_input("Напиши сообщение", disabled=not confirmed)
    pending = ss.pop("pending", None)
    if pending and confirmed:
        prompt = pending

    if prompt:
        ss.messages.append({"role": "user", "text": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        with st.spinner("Проверяю и маскирую..."):
            result = handle(prompt, provider_name, strict, detector)
        record(result)
        msg = {"role": "assistant", "text": reply_for(result),
               "badges": badges(result.get("found", {})),
               "masked": result.get("masked")}
        ss.messages.append(msg)
        with st.chat_message("assistant"):
            render_assistant(msg, show_masked)

elif mode == "🔬 Демо":
    st.subheader("Что видит каждая сторона")
    with st.expander("Готовые примеры", expanded=True):
        cols = st.columns(3)
        for i, (title, text) in enumerate(EXAMPLES.items()):
            cols[i % 3].button(title, key=f"demo_{i}", on_click=set_demo,
                               args=(text,))
    st.text_area("Сообщение пользователя", key="demo_text", height=110)
    if st.button("Обработать", type="primary", disabled=not confirmed):
        text = ss.demo_text.strip()
        if not text:
            st.warning("Сообщение пустое.")
        else:
            result = handle(text, provider_name, strict, detector)
            record(result)
            a, b, c = st.columns(3)
            with a.container(border=True):
                st.markdown("**1. Оригинал**")
                st.code(text, language=None)
                st.caption("Остаётся только у пользователя.")
            with b.container(border=True):
                st.markdown("**2. Уйдёт модели**")
                if result["masked"] is None:
                    st.error(reply_for(result))
                else:
                    st.code(result["masked"], language=None)
                    st.caption("Модель получает только этот текст.")
            with c.container(border=True):
                st.markdown("**3. Ответ пользователю**")
                if result["status"] == "ok":
                    st.code(result["answer"], language=None)
                    st.caption("Пароли, ключи, карты и счета не возвращаются.")
                else:
                    st.error(reply_for(result))
            if result["found"]:
                st.markdown(badges(result["found"]), unsafe_allow_html=True)
            else:
                st.write("Чувствительных данных не найдено.")

else:
    st.subheader("🔐 Шифрованный журнал")
    audit = get_audit()
    if audit is None:
        st.info("Журнал выключен: в .env нет AUDIT_KEY (создаётся `python gen_key.py`).")
    else:
        try:
            events = audit.read_all()
        except Exception:
            st.error("Журнал не расшифровался: ключ в .env не подходит к файлу.")
            events = []
        rows = [{
            "Время": time.strftime("%d.%m %H:%M:%S", time.localtime(e["ts"])),
            "Статус": e["status"],
            "Провайдер": e["provider"],
            "Находки": ", ".join(f"{k}×{v}" for k, v in sorted(e["found"].items())),
            "Типы цензора": ", ".join(e["kinds"]),
        } for e in reversed(events[-50:])]
        if rows:
            st.dataframe(rows)
        else:
            st.write("Записей пока нет.")
        st.caption("Файл logs/audit.enc зашифрован AES-256-GCM. Здесь только "
                   "статус и типы находок, исходных данных в журнале нет.")

st.divider()
st.caption("Маскирование снижает риск утечки, но не даёт абсолютной гарантии. "
           "Секретные и служебные данные в облако отправлять нельзя.")
