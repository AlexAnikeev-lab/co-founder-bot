# ✅ Виртуальное окружение настроено с Python 3.12

## Что сделано

✅ Создано виртуальное окружение с Python 3.12.12
✅ Окружение готово к установке зависимостей

## Следующие шаги

Когда у вас будет доступ к интернету, выполните:

```bash
cd "/Users/alex/Desktop/Telegram Bots/Business/Co-founder-new"

# Активируйте виртуальное окружение
source .venv/bin/activate

# Обновите pip
pip install --upgrade pip setuptools wheel

# Установите зависимости
pip install -r requirements.txt
```

## Проверка установки

После установки проверьте:

```bash
# Активируйте окружение
source .venv/bin/activate

# Проверьте версию Python (должна быть 3.12.x)
python --version

# Проверьте установленные пакеты
pip list
```

## Инициализация базы данных

После установки зависимостей:

```bash
source .venv/bin/activate
python init_db.py
```

## Запуск бота

```bash
source .venv/bin/activate
python main.py
```

## Быстрая команда для активации

Добавьте в `~/.zshrc` алиас для быстрой активации:

```bash
alias cofounder="cd '/Users/alex/Desktop/Telegram Bots/Business/Co-founder-new' && source .venv/bin/activate"
```

После этого можно просто написать `cofounder` для перехода в проект и активации окружения.
