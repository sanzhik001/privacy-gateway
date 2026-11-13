"""Сканер документов: ищет персональные и секретные данные."""

import csv
import io
import os

import streamlit as st
from dotenv import load_dotenv

from src.doc_reader import read_document
from src.ollama_detector import find_entities, list_models
from src.scanner import RISK_LABELS, RISK_ORDER, report_rows, scan_text

load_dotenv()
st.set_page_config(page_title="Сканер документов", page_icon="📄",
                   layout="wide")

MAX_BYTES = 5 * 1024 * 1024

password = os.getenv("CHAT_PASSWORD")
if password and not st.session_state.get("auth"):
    st.title("📄 Сканер документов")
    entered = st.text_input("Пароль доступа", type="password")
    if entered and entered == password:
        st.session_state.auth = True
        st.rerun()
    elif entered:
        st.error("Неверный пароль")
    st.stop()


def csv_safe(value):
    """Защита от формул в Excel: значение не должно начинаться с =, +, -, @."""
    s = str(value)
    return "'" + s if s[:1] in ("=", "+", "-", "@") else s


with st.sidebar:
    st.markdown("## 📄 Сканер")
    use_ollama = st.checkbox("Искать имена и организации через Ollama")
    model = None
    if use_ollama:
        try:
            models = list_models()
        except RuntimeError as e:
            models = []
            st.error(str(e))
        if models:
            model = st.selectbox("Модель", models)
    st.caption("Документ не отправляется в интернет. Правила работают "
               "локально, а Ollama принимает запросы только на localhost.")

st.title("📄 Сканер документов")
st.caption("Находит ФИО, ИИН и БИН, карты, счета, пароли, ключи и другие "
           "данные. Учебный прототип: используй искусственные документы.")

uploaded = st.file_uploader("Документ (txt, md, csv, docx, pdf, до 5 МБ)",
                            type=["txt", "md", "csv", "docx", "pdf"])
pasted = st.text_area("…или вставь текст", height=140)

text = ""
if uploaded is not None:
    if uploaded.size > MAX_BYTES:
        st.error("Файл больше 5 МБ.")
    else:
        try:
            text = read_document(uploaded.name, uploaded.getvalue())
        except Exception as e:
            st.error(f"Не удалось прочитать файл: {type(e).__name__}")
        else:
            if not text.strip():
                st.warning("Текст не извлечён. Если это скан PDF, нужно "
                           "распознавание (OCR), его в проекте нет.")
if not text.strip() and pasted.strip():
    text = pasted

if text.strip() and use_ollama and model:
    st.caption(f"Ollama обработает примерно {len(text) // 3000 + 1} фрагм. "
               "по 3000 символов, каждый отдельным запросом.")

if st.button("Сканировать", type="primary", disabled=not text.strip()):
    extra = None
    if use_ollama and model:
        with st.spinner("Ollama анализирует документ, это может занять время…"):
            try:
                extra = find_entities(text, model)
            except RuntimeError as e:
                st.warning(f"{e} Продолжаю только правилами.")
    with st.spinner("Сканирую…"):
        st.session_state.scan = scan_text(text, extra)
    st.session_state.scan_ollama = bool(extra)

res = st.session_state.get("scan")
if res:
    s = res["summary"]
    cols = st.columns(4)
    cols[0].metric("Всего значений", sum(s.values()))
    for col, risk in zip(cols[1:], RISK_ORDER):
        col.metric(RISK_LABELS[risk], s[risk])
    if st.session_state.get("scan_ollama"):
        st.caption("Использована Ollama: проверены только имена и "
                   "организации, дословно найденные в тексте.")
    if res["blocked_phrases"]:
        st.error("Запрещённые фразы: " + ", ".join(res["blocked_phrases"]))

    if not res["findings"]:
        st.success("Правила ничего не нашли. Это не гарантия: имя вне "
                   "словаря и без триггера пройдёт.")
    else:
        full = st.checkbox("Показывать значения целиком", value=False)
        st.dataframe(report_rows(res, full=full))

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Риск", "Тип", "Значение (скрыто)", "Вхождений",
                         "Строки"])
        for r in report_rows(res):
            writer.writerow([r["Риск"], r["Тип"], csv_safe(r["Значение"]),
                             r["Вхождений"], r["Строки"]])
        st.download_button("⬇️ Отчёт (CSV, значения скрыты)",
                           buf.getvalue().encode("utf-8-sig"),
                           "report.csv", "text/csv")
        st.download_button("⬇️ Очищенный текст (TXT)",
                           res["masked"].encode("utf-8"),
                           "masked.txt", "text/plain")
        with st.expander("Очищенный текст"):
            st.text_area("Очищенный текст", res["masked"], height=300,
                         label_visibility="collapsed")
