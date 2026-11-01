import logging
from dataclasses import dataclass
from datetime import date, datetime

from playwright.async_api import async_playwright

from src.date_parser import calculate_scroll_depth

logger = logging.getLogger(__name__)


@dataclass
class TelegramPost:
    channel: str
    post_id: str
    text: str
    datetime: datetime
    link: str


def parse_channel_link(text: str) -> str:
    text = text.strip()

    if "t.me/" in text:
        parts = text.split("t.me/")[-1].split("/")
        if parts[0] == "s" and len(parts) > 1:
            return parts[1].split("?")[0].lower()
        return parts[0].split("?")[0].lower()

    if text.startswith("@"):
        return text[1:].lower()

    return text.lower()


async def verify_channel_exists(channel: str) -> bool:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            response = await page.goto(
                f"https://t.me/s/{channel}",
                wait_until="domcontentloaded",
                timeout=15000
            )

            if response is None or response.status != 200:
                return False

            await page.wait_for_timeout(1000)

            messages = await page.locator(".tgme_widget_message_wrap").count()
            return messages > 0
        except Exception as e:
            logger.error(f"Error verifying channel {channel}: {e}")
            return False
        finally:
            await browser.close()


async def parse_channel(
    channel: str,
    start_date: date,
    end_date: date,
    status_callback: callable | None = None
) -> list[TelegramPost]:
    posts: list[TelegramPost] = []
    max_scrolls = calculate_scroll_depth(start_date)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(
                f"https://t.me/s/{channel}",
                wait_until="domcontentloaded",
                timeout=30000
            )

            await page.wait_for_selector(
                ".tgme_widget_message_wrap",
                timeout=10000
            )

            scroll_count = 0
            reached_target_date = False
            last_post_count = 0
            no_new_posts_count = 0

            while scroll_count < max_scrolls and not reached_target_date:
                message_wraps = await page.locator(".tgme_widget_message_wrap").all()
                current_count = len(message_wraps)

                if current_count == last_post_count:
                    no_new_posts_count += 1
                    if no_new_posts_count >= 3:
                        break
                else:
                    no_new_posts_count = 0
                    last_post_count = current_count

                if message_wraps:
                    oldest_message = message_wraps[-1]
                    time_element = oldest_message.locator("time[datetime]").first

                    try:
                        datetime_attr = await time_element.get_attribute("datetime")
                        if datetime_attr:
                            post_date = datetime.fromisoformat(
                                datetime_attr
                            ).date()

                            if post_date < start_date:
                                reached_target_date = True
                                break
                    except Exception:
                        pass

                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(800)
                scroll_count += 1

                if status_callback and scroll_count % 5 == 0:
                    progress = min(100, int((scroll_count / max_scrolls) * 100))
                    await status_callback(f"Загрузка @{channel}: {progress}%")

            message_wraps = await page.locator(".tgme_widget_message_wrap").all()

            for wrap in message_wraps:
                try:
                    message_div = wrap.locator(".tgme_widget_message").first
                    data_post = await message_div.get_attribute("data-post")

                    if not data_post:
                        continue

                    post_id = data_post.split("/")[-1] if "/" in data_post else data_post

                    time_element = wrap.locator("time[datetime]").first
                    datetime_attr = await time_element.get_attribute("datetime")

                    if not datetime_attr:
                        continue

                    post_datetime = datetime.fromisoformat(
                        datetime_attr
                    )
                    post_date = post_datetime.date()

                    if post_date < start_date or post_date > end_date:
                        continue

                    text_element = wrap.locator(".tgme_widget_message_text").first
                    text = ""

                    try:
                        if await text_element.count() > 0:
                            text = await text_element.inner_text()
                    except Exception:
                        pass

                    if not text.strip():
                        continue

                    posts.append(TelegramPost(
                        channel=channel,
                        post_id=post_id,
                        text=text.strip(),
                        datetime=post_datetime,
                        link=f"https://t.me/{channel}/{post_id}"
                    ))

                except Exception as e:
                    logger.debug(f"Error parsing post: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing channel {channel}: {e}")
        finally:
            await browser.close()

    posts.sort(key=lambda x: x.datetime, reverse=True)
    return posts


async def parse_multiple_channels(
    channels: list[str],
    start_date: date,
    end_date: date,
    status_callback: callable | None = None
) -> dict[str, list[TelegramPost]]:
    results: dict[str, list[TelegramPost]] = {}

    for channel in channels:
        if status_callback:
            await status_callback(f"Парсинг канала @{channel}...")

        posts = await parse_channel(channel, start_date, end_date, status_callback)
        results[channel] = posts

        if status_callback:
            await status_callback(f"@{channel}: найдено {len(posts)} постов")

    return results
