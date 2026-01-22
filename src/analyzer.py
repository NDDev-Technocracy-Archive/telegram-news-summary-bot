import json
import logging
from dataclasses import dataclass
from typing import Optional

from openai import AsyncOpenAI

from src.config import settings
from src.channel_parser import TelegramPost

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


@dataclass
class SelectedPost:
    post: TelegramPost
    reason: str


@dataclass
class AnalysisResult:
    summary: str
    selected_posts: list[SelectedPost]
    total_analyzed: int


def clean_json_response(text: str) -> str:
    text = text.strip()

    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


def truncate_text(text: str, max_length: int = 500) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


async def analyze_posts(
    posts: list[TelegramPost],
    topic: Optional[str] = None
) -> AnalysisResult:
    if not posts:
        return AnalysisResult(
            summary="Посты не найдены за указанный период.",
            selected_posts=[],
            total_analyzed=0
        )

    posts_text = ""
    post_map: dict[int, TelegramPost] = {}

    for idx, post in enumerate(posts, 1):
        post_map[idx] = post
        truncated = truncate_text(post.text)
        posts_text += f"{idx}. [{post.channel}] {truncated}\n\n"

    topic_instruction = ""
    if topic:
        topic_instruction = f"""
ВАЖНО: Пользователь интересуется темой "{topic}".
Выбирай ТОЛЬКО посты, которые релевантны этой теме.
Если релевантных постов нет - так и напиши в резюме.
"""

    system_prompt = """Ты аналитик новостей из Telegram каналов.
Твоя задача - проанализировать посты и выбрать самые интересные и важные.

Отвечай СТРОГО в формате JSON без дополнительного текста.
"""

    user_prompt = f"""Проанализируй следующие посты из Telegram каналов:

{posts_text}

{topic_instruction}

Задачи:
1. Выбери 5-10 самых интересных/важных постов (можно меньше, если постов мало или они неинтересные)
2. Для каждого выбранного поста напиши краткое объяснение (1-2 предложения) почему он интересен
3. Напиши общее резюме дня/периода на русском языке (3-5 предложений)

Формат ответа (строго JSON):
{{
    "summary": "Общее резюме дня...",
    "selected_posts": [
        {{"post_id": 1, "reason": "Почему этот пост интересен..."}},
        {{"post_id": 2, "reason": "Почему этот пост интересен..."}}
    ]
}}

ВАЖНО: post_id должен соответствовать номеру поста в списке выше (1, 2, 3 и т.д.)
"""

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from GPT")

        cleaned = clean_json_response(content)
        data = json.loads(cleaned)

        selected_posts: list[SelectedPost] = []
        for item in data.get("selected_posts", []):
            post_id = item.get("post_id")
            reason = item.get("reason", "")

            if post_id and post_id in post_map:
                selected_posts.append(SelectedPost(
                    post=post_map[post_id],
                    reason=reason
                ))

        return AnalysisResult(
            summary=data.get("summary", "Резюме не сформировано."),
            selected_posts=selected_posts,
            total_analyzed=len(posts)
        )

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        logger.error(f"Raw response: {content if 'content' in dir() else 'N/A'}")
        return AnalysisResult(
            summary="Ошибка анализа: не удалось разобрать ответ GPT.",
            selected_posts=[],
            total_analyzed=len(posts)
        )
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return AnalysisResult(
            summary=f"Ошибка анализа: {str(e)}",
            selected_posts=[],
            total_analyzed=len(posts)
        )


def format_analysis_result(result: AnalysisResult, date_range_str: str) -> str:
    lines = [
        f"📊 Анализ новостей {date_range_str}",
        f"📝 Проанализировано постов: {result.total_analyzed}",
        "",
        "📌 Резюме:",
        result.summary,
        "",
    ]

    if result.selected_posts:
        lines.append(f"⭐ Интересные посты ({len(result.selected_posts)}):")
        lines.append("")

        for idx, sp in enumerate(result.selected_posts, 1):
            lines.append(f"{idx}. @{sp.post.channel}")
            lines.append(f"   💡 {sp.reason}")
            lines.append(f"   🔗 {sp.post.link}")
            lines.append("")
    else:
        lines.append("Интересных постов не найдено.")

    return "\n".join(lines)
