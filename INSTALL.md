# Инструкция по установке зависимостей

## Проблема с установкой pydantic-core

Если при установке зависимостей возникает ошибка компиляции `pydantic-core`, это означает, что требуется Rust компилятор.

## Решения

### Вариант 1: Установка Rust через rustup (РЕКОМЕНДУЕТСЯ, не требует sudo)

Rust устанавливается в домашнюю директорию и не требует прав администратора:

1. Установите Rust через rustup:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

2. После установки добавьте Rust в PATH:
```bash
source $HOME/.cargo/env
```

3. Проверьте установку:
```bash
rustc --version
cargo --version
```

4. Установите зависимости:
```bash
cd "/Users/alex/Desktop/Telegram Bots/Business/Co-founder-new"
source .venv/bin/activate
pip install -r requirements.txt
```

**Важно:** После установки Rust нужно перезагрузить терминал или выполнить `source $HOME/.cargo/env` в каждом новом терминале.

### Вариант 2: Использование только binary wheels

Если не хотите устанавливать Rust, попробуйте установить только предкомпилированные пакеты:

```bash
pip install --only-binary :all: -r requirements.txt
```

**Примечание:** Этот метод может не сработать, если для вашей версии Python нет предкомпилированных wheels.

### Вариант 3: Использование Python 3.10-3.12

Python 3.14 очень новый, и некоторые библиотеки могут не иметь wheels для этой версии. Рекомендуется использовать Python 3.10, 3.11 или 3.12:

```bash
# Создайте новое виртуальное окружение с Python 3.12
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Вариант 4: Установка зависимостей по одной

Если проблемы продолжаются, попробуйте установить зависимости по одной:

```bash
pip install aiogram
pip install aiosqlite
pip install python-dotenv
pip install sqlalchemy
pip install alembic
pip install openai
```

## Проверка установки

После установки проверьте, что все зависимости установлены:

```bash
pip list | grep -E "aiogram|aiosqlite|sqlalchemy|alembic|openai"
```

## Дополнительная информация

- Rust необходим для компиляции некоторых Python пакетов, написанных на Rust
- `pydantic-core` - это зависимость `pydantic`, которая используется в `aiogram`
- Если проблемы продолжаются, проверьте версию Python и наличие интернет-соединения
