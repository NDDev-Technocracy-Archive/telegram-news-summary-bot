# Telegram News Summary Bot

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-blue.svg)](https://aiogram.dev)

Telegram-бот для агрегации и анализа новостей из публичных Telegram каналов с использованием GPT.

## Возможности

- **Парсинг публичных каналов** - автоматический сбор постов через Playwright без авторизации
- **Умный парсинг дат** - понимает "вчера", "за неделю", "18 января", даты в любом месте текста
- **GPT анализ** - выбор 5-10 самых интересных постов с объяснениями и общее резюме
- **Фильтрация по теме** - запрос "AI за неделю" покажет только посты про AI
- **Динамический скроллинг** - глубина загрузки адаптируется под запрошенный период
- **SQLite хранение** - данные пользователей и каналов сохраняются локально

## Технологии

| Компонент | Технология |
|-----------|------------|
| Telegram Bot | aiogram 3.x |
| Web Scraping | Playwright (Chromium) |
| AI Analysis | OpenAI GPT-4o-mini |
| Database | SQLite + aiosqlite |
| Config | Pydantic Settings |

## Установка

### Требования

- Python 3.11+
- Telegram Bot Token (от [@BotFather](https://t.me/BotFather))
- OpenAI API Key

### Шаги установки

```bash
# Клонировать репозиторий
git clone https://github.com/yourusername/telegram-news-summary-bot.git
cd telegram-news-summary-bot

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# или
.\venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Установить браузер для Playwright
playwright install chromium

# Создать файл конфигурации
cp .env.example .env
```

### Конфигурация

Отредактируйте `.env` файл:

```env
TELEGRAM_BOT_TOKEN=your_token_from_botfather
OPENAI_API_KEY=sk-your_openai_api_key
```

Опциональные настройки:

```env
DATABASE_PATH=bot.db          # Путь к базе данных
MAX_CHANNELS_PER_USER=10      # Лимит каналов на пользователя
MAX_SCROLLS=100               # Максимум скроллов при парсинге
OPENAI_MODEL=gpt-4o-mini      # Модель OpenAI
```

## Запуск

```bash
source venv/bin/activate
python -m src.bot
```

## Использование

### Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Начало работы |
| `/add <ссылка>` | Добавить канал |
| `/my_channels` | Список каналов |
| `/remove <название>` | Удалить канал |
| `/summary [дата] [тема]` | Получить анализ |
| `/help` | Справка |

### Форматы каналов

Бот понимает разные форматы ссылок:

```
/add t.me/s/durov
/add t.me/durov
/add @durov
/add durov
```

### Форматы дат

```
/summary                    # сегодня
/summary вчера              # вчера
/summary позавчера          # позавчера
/summary за неделю          # последние 7 дней
/summary за 3 дня           # последние 3 дня
/summary 20.01.2025         # конкретная дата
/summary 18 января          # дата текущего года
```

### Фильтрация по теме

Тема может быть в любом месте запроса:

```
/summary AI за неделю           # AI за последнюю неделю
/summary вчера криптовалюта     # крипта за вчера
/summary что нового про Python  # Python за сегодня
```

## Архитектура

```
src/
├── bot.py              # Точка входа, инициализация
├── config.py           # Pydantic Settings конфигурация
├── database.py         # SQLite операции (aiosqlite)
├── date_parser.py      # Парсинг дат из текста
├── channel_parser.py   # Playwright парсинг каналов
├── analyzer.py         # OpenAI GPT анализ
└── handlers.py         # Обработчики команд aiogram
```

### Поток данных

```
User Command → handlers.py → channel_parser.py → analyzer.py → Response
                    ↓              ↓
              database.py    Playwright scraping
                    ↓              ↓
                SQLite        t.me/s/channel
```

### Алгоритм парсинга дат

1. Ключевые слова: `сегодня`, `вчера`, `позавчера`
2. Диапазоны: `за неделю`, `за N дней`
3. Конкретные даты: `20.01.2025`, `18 января`
4. Остаток текста после извлечения даты = тема

### Динамический скроллинг

| Период | Скроллов |
|--------|----------|
| Сегодня | 5 |
| Вчера | 10 |
| 3 дня | 20 |
| Неделя | 40 |
| 2 недели | 60 |
| Месяц | 80-100 |

## Разработка

### Структура базы данных

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE channels (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    channel_name TEXT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, channel_name)
);
```

### Важные особенности кода

**aiosqlite с asynccontextmanager:**
```python
@asynccontextmanager
async def get_connection():
    conn = await aiosqlite.connect("bot.db")
    try:
        yield conn
    finally:
        await conn.close()

# Использование (БЕЗ await перед get_connection):
async with get_connection() as conn:
    cursor = await conn.execute("SELECT ...")
```

**aiogram 3.x Router:**
```python
router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Hello!")
```

**Очистка JSON от markdown:**
```python
def clean_json_response(text: str) -> str:
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
```

## Contributing

См. [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT License - см. [LICENSE](LICENSE)

## Автор

Создано с использованием Claude Code.
