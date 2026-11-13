#!/bin/zsh
cd "$(dirname "$0")"
source .venv/bin/activate
if ! curl -s --max-time 3 http://localhost:11434/api/tags > /dev/null; then
  echo "⚠️  Ollama не запущена: детектор имён будет недоступен. Открой приложение Ollama."
fi
python -m pytest -q > /tmp/pg_tests.txt 2>&1 || {
  echo "⛔ Тесты не прошли, запуск остановлен:"; tail -5 /tmp/pg_tests.txt; exit 1; }
echo "✅ Тесты пройдены. Открываю чат (только на этом компьютере)."
streamlit run chat.py --server.address 127.0.0.1
