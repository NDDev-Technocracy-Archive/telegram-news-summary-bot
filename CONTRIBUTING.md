# Contributing

Спасибо за интерес к проекту! Мы рады любым контрибуциям.

## Как внести вклад

### Сообщить о баге

1. Проверьте, что баг еще не был зарепорчен в [Issues](https://github.com/yourusername/telegram-news-summary-bot/issues)
2. Создайте новый Issue с описанием:
   - Что ожидалось
   - Что произошло на самом деле
   - Шаги для воспроизведения
   - Версия Python и ОС

### Предложить улучшение

1. Создайте Issue с тегом `enhancement`
2. Опишите предложение и почему оно полезно
3. Если возможно, предложите вариант реализации

### Отправить Pull Request

1. Форкните репозиторий
2. Создайте ветку для изменений:
   ```bash
   git checkout -b feature/my-feature
   ```
3. Внесите изменения
4. Проверьте код:
   ```bash
   # Проверка синтаксиса
   python -m py_compile src/*.py
   ```
5. Закоммитьте с понятным сообщением:
   ```bash
   git commit -m "feat: add new date format support"
   ```
6. Отправьте PR в `main` ветку

## Стиль кода

- Python 3.11+ с type hints
- Форматирование: PEP 8
- Docstrings: Google style
- Асинхронный код везде где возможно

### Примеры

```python
async def parse_channel(
    channel: str,
    start_date: date,
    end_date: date,
) -> list[TelegramPost]:
    """Parse posts from a public Telegram channel.

    Args:
        channel: Channel username without @
        start_date: Start of date range
        end_date: End of date range

    Returns:
        List of parsed posts within date range
    """
    ...
```

## Commit messages

Используем [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - новая функциональность
- `fix:` - исправление бага
- `docs:` - изменения в документации
- `refactor:` - рефакторинг без изменения функциональности
- `test:` - добавление тестов
- `chore:` - обновление зависимостей, конфигов

## Области для контрибуции

- Поддержка новых форматов дат
- Улучшение парсинга каналов
- Кэширование результатов
- Тесты
- Документация
- Локализация на другие языки

## Вопросы?

Создайте Issue с тегом `question` или напишите в Discussions.
