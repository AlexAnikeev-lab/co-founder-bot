#!/usr/bin/env bash
# Запуск тестового бота через ENV_FILE=.env.test
# Альтернатива: TEST_MODE=true в .env и python main.py
set -euo pipefail
cd "$(dirname "$0")"

if [[ -x ".venv/bin/python" ]]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python3"
fi

export ENV_FILE=".env.test"
export PYTHONUNBUFFERED=1
exec "$PYTHON" main.py
