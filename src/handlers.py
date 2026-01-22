import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from src.config import settings
from src.database import (
    get_or_create_user,
    add_channel,
    get_user_channels,
    remove_channel,
)
from src.channel_parser import (
    parse_channel_link,
    verify_channel_exists,
    parse_multiple_channels,
)
from src.date_parser import parse_user_input, format_date_range
from src.analyzer import analyze_posts, format_analysis_result

logger = logging.getLogger(__name__)
router = Router()


HELP_TEXT = """
📚 Команды бота:

/start - Начало работы
/add <ссылка> - Добавить канал для отслеживания
/my_channels - Показать мои каналы
/remove <название> - Удалить канал
/summary [дата] [тема] - Получить анализ новостей
/help - Справка

📝 Форматы ссылок на канал:
• t.me/s/channel_name
• t.me/channel_name
• @channel_name
• channel_name

📅 Форматы даты для /summary:
• сегодня, вчера, позавчера
• за неделю, за 3 дня
• 20.01.2025, 2025-01-20
• 20.01, 18 января

💡 Примеры использования /summary:
• /summary - новости за сегодня
• /summary вчера - новости за вчера
• /summary AI за неделю - новости про AI за неделю
• /summary криптовалюта 20.01 - про крипту за 20 января
"""


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_id = await get_or_create_user(message.from_user.id)

    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я бот для анализа новостей из Telegram каналов.\n\n"
        "🔹 Добавьте каналы командой /add\n"
        "🔹 Получайте саммари командой /summary\n\n"
        f"📌 Лимит: {settings.MAX_CHANNELS_PER_USER} каналов\n\n"
        "Напишите /help для справки."
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("add"))
async def cmd_add(message: Message) -> None:
    user_id = await get_or_create_user(message.from_user.id)

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "❌ Укажите ссылку на канал.\n\n"
            "Примеры:\n"
            "/add t.me/durov\n"
            "/add @telegram\n"
            "/add channel_name"
        )
        return

    channel_name = parse_channel_link(args[1])

    if not channel_name:
        await message.answer("❌ Не удалось распознать название канала.")
        return

    status_msg = await message.answer(f"🔍 Проверяю канал @{channel_name}...")

    exists = await verify_channel_exists(channel_name)

    if not exists:
        await status_msg.edit_text(
            f"❌ Канал @{channel_name} не найден или не является публичным.\n\n"
            "Убедитесь, что:\n"
            "• Канал существует\n"
            "• Канал публичный (не приватный)"
        )
        return

    success, msg = await add_channel(user_id, channel_name)

    if success:
        await status_msg.edit_text(f"✅ {msg}")
    else:
        await status_msg.edit_text(f"❌ {msg}")


@router.message(Command("my_channels"))
async def cmd_my_channels(message: Message) -> None:
    user_id = await get_or_create_user(message.from_user.id)

    channels = await get_user_channels(user_id)

    if not channels:
        await message.answer(
            "📭 У вас пока нет добавленных каналов.\n\n"
            "Добавьте канал командой /add"
        )
        return

    channels_list = "\n".join([f"• @{ch}" for ch in channels])
    await message.answer(
        f"📋 Ваши каналы ({len(channels)}/{settings.MAX_CHANNELS_PER_USER}):\n\n"
        f"{channels_list}\n\n"
        "Удалить канал: /remove название"
    )


@router.message(Command("remove"))
async def cmd_remove(message: Message) -> None:
    user_id = await get_or_create_user(message.from_user.id)

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "❌ Укажите название канала для удаления.\n\n"
            "Пример: /remove durov"
        )
        return

    channel_name = parse_channel_link(args[1])
    success, msg = await remove_channel(user_id, channel_name)

    if success:
        await message.answer(f"✅ {msg}")
    else:
        await message.answer(f"❌ {msg}")


@router.message(Command("summary"))
async def cmd_summary(message: Message) -> None:
    user_id = await get_or_create_user(message.from_user.id)

    channels = await get_user_channels(user_id)

    if not channels:
        await message.answer(
            "📭 У вас нет добавленных каналов.\n\n"
            "Сначала добавьте каналы командой /add"
        )
        return

    args = message.text.split(maxsplit=1)
    query_text = args[1] if len(args) > 1 else ""

    parsed = parse_user_input(query_text)
    date_range_str = format_date_range(parsed.start_date, parsed.end_date)

    topic_info = f"\n🎯 Тема: {parsed.topic}" if parsed.topic else ""

    status_msg = await message.answer(
        f"🔄 Начинаю анализ...\n\n"
        f"📅 Период: {date_range_str}{topic_info}\n"
        f"📺 Каналов: {len(channels)}"
    )

    async def update_status(text: str):
        try:
            await status_msg.edit_text(
                f"🔄 {text}\n\n"
                f"📅 Период: {date_range_str}{topic_info}"
            )
        except Exception:
            pass

    try:
        await update_status("Парсинг каналов...")

        channel_posts = await parse_multiple_channels(
            channels=channels,
            start_date=parsed.start_date,
            end_date=parsed.end_date,
            status_callback=update_status
        )

        all_posts = []
        for posts in channel_posts.values():
            all_posts.extend(posts)

        if not all_posts:
            await status_msg.edit_text(
                f"📭 Посты не найдены за {date_range_str}.\n\n"
                "Попробуйте:\n"
                "• Указать другую дату\n"
                "• Добавить больше каналов"
            )
            return

        await update_status(f"Анализ {len(all_posts)} постов с помощью GPT...")

        result = await analyze_posts(
            posts=all_posts,
            topic=parsed.topic
        )

        formatted = format_analysis_result(result, date_range_str)

        if len(formatted) > 4096:
            parts = [formatted[i:i+4096] for i in range(0, len(formatted), 4096)]
            await status_msg.delete()
            for part in parts:
                await message.answer(part)
        else:
            await status_msg.edit_text(formatted)

    except Exception as e:
        logger.error(f"Summary error: {e}")
        await status_msg.edit_text(
            f"❌ Произошла ошибка при анализе.\n\n"
            f"Попробуйте позже или обратитесь к администратору."
        )
