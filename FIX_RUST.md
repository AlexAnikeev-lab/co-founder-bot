# Решение проблемы с установкой зависимостей

## Проблема
Ошибка компиляции `pydantic-core` из-за отсутствия Rust компилятора.

## Решение: Установка Rust

### Вариант 1: Установка Rust через rustup (рекомендуется, не требует sudo)

Rust устанавливается в домашнюю директорию и не требует прав администратора:

```bash
# Скачайте и установите Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# После установки добавьте Rust в PATH (выберите вариант 1 при запросе)
# Или выполните вручную:
source $HOME/.cargo/env

# Проверьте установку
rustc --version
cargo --version
```

После установки Rust попробуйте установить зависимости:

```bash
cd "/Users/alex/Desktop/Telegram Bots/Business/Co-founder-new"
source .venv/bin/activate
pip install -r requirements.txt
```

### Вариант 2: Установка Python 3.12 через Homebrew

Если у вас есть права администратора или можете исправить права Homebrew:

```bash
# Исправление прав (если нужно)
sudo chown -R $(whoami) /opt/homebrew

# Установка Python 3.12
brew install python@3.12

# Создание нового виртуального окружения с Python 3.12
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Вариант 3: Использование только binary wheels (может не сработать для Python 3.14)

```bash
source .venv/bin/activate
pip install --only-binary :all: -r requirements.txt
```

**Примечание:** Для Python 3.14 может не быть предкомпилированных wheels для всех пакетов.

## Проверка установки

После установки Rust или Python 3.12:

```bash
# Проверка Rust
rustc --version

# Или проверка Python
python3.12 --version

# Установка зависимостей
source .venv/bin/activate
pip install -r requirements.txt
```

## Если проблемы с интернетом

Если возникают проблемы с подключением к PyPI:

1. Проверьте интернет-соединение
2. Попробуйте использовать другой DNS (например, 8.8.8.8)
3. Проверьте настройки прокси/файрвола

## Альтернативное решение

Если ничего не помогает, можно использовать Docker с предустановленным Python и Rust:

```bash
# Создайте Dockerfile
cat > Dockerfile << EOF
FROM python:3.12-slim
RUN apt-get update && apt-get install -y build-essential
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
EOF

# Соберите образ
docker build -t cofounder-bot .

# Запустите контейнер
docker run -it cofounder-bot
```
