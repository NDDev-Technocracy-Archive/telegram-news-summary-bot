import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional


MONTHS_RU = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
    "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
    "январь": 1, "февраль": 2, "март": 3, "апрель": 4,
    "май": 5, "июнь": 6, "июль": 7, "август": 8,
    "сентябрь": 9, "октябрь": 10, "ноябрь": 11, "декабрь": 12,
}


@dataclass
class ParsedQuery:
    start_date: date
    end_date: date
    topic: Optional[str]


def parse_user_input(text: str) -> ParsedQuery:
    text = text.strip()
    original_text = text
    today = date.today()

    start_date: Optional[date] = None
    end_date: Optional[date] = None
    matched_span: Optional[tuple[int, int]] = None

    keywords_single = {
        "сегодня": 0,
        "today": 0,
        "вчера": 1,
        "yesterday": 1,
        "позавчера": 2,
    }

    text_lower = text.lower()

    for keyword, days_ago in keywords_single.items():
        pattern = rf"\b{keyword}\b"
        match = re.search(pattern, text_lower)
        if match:
            target_date = today - timedelta(days=days_ago)
            start_date = target_date
            end_date = target_date
            matched_span = match.span()
            break

    if start_date is None:
        range_patterns = [
            (r"за\s+последн(?:ие|юю|ий)\s+(\d+)\s+(?:дн(?:ей|я)|день)", "days"),
            (r"за\s+(\d+)\s+(?:дн(?:ей|я)|день)", "days"),
            (r"за\s+неделю", "week"),
            (r"за\s+последнюю\s+неделю", "week"),
            (r"за\s+месяц", "month"),
            (r"за\s+последний\s+месяц", "month"),
        ]

        for pattern, range_type in range_patterns:
            match = re.search(pattern, text_lower)
            if match:
                if range_type == "days":
                    days = int(match.group(1))
                    start_date = today - timedelta(days=days - 1)
                    end_date = today
                elif range_type == "week":
                    start_date = today - timedelta(days=6)
                    end_date = today
                elif range_type == "month":
                    start_date = today - timedelta(days=29)
                    end_date = today
                matched_span = match.span()
                break

    if start_date is None:
        date_patterns = [
            (r"(\d{1,2})\.(\d{1,2})\.(\d{4})", "dmy_full"),
            (r"(\d{4})-(\d{1,2})-(\d{1,2})", "ymd"),
            (r"(\d{1,2})\.(\d{1,2})(?!\.\d)", "dm"),
            (r"(\d{1,2})\s+(" + "|".join(MONTHS_RU.keys()) + r")\s+(\d{4})", "d_month_y"),
            (r"(\d{1,2})\s+(" + "|".join(MONTHS_RU.keys()) + r")(?!\s+\d{4})", "d_month"),
        ]

        for pattern, fmt in date_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    if fmt == "dmy_full":
                        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                        start_date = date(year, month, day)
                    elif fmt == "ymd":
                        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                        start_date = date(year, month, day)
                    elif fmt == "dm":
                        day, month = int(match.group(1)), int(match.group(2))
                        year = today.year
                        start_date = date(year, month, day)
                        if start_date > today:
                            start_date = date(year - 1, month, day)
                    elif fmt == "d_month_y":
                        day = int(match.group(1))
                        month = MONTHS_RU[match.group(2)]
                        year = int(match.group(3))
                        start_date = date(year, month, day)
                    elif fmt == "d_month":
                        day = int(match.group(1))
                        month = MONTHS_RU[match.group(2)]
                        year = today.year
                        start_date = date(year, month, day)
                        if start_date > today:
                            start_date = date(year - 1, month, day)

                    end_date = start_date
                    matched_span = match.span()
                    break
                except ValueError:
                    continue

    if start_date is None:
        start_date = today
        end_date = today

    topic: Optional[str] = None
    if matched_span:
        before = original_text[:matched_span[0]]
        after = original_text[matched_span[1]:]
        remaining = f"{before} {after}".strip()

        remaining = re.sub(r"\bза\b", "", remaining, flags=re.IGNORECASE)
        remaining = re.sub(r"\bпро\b", "", remaining, flags=re.IGNORECASE)
        remaining = re.sub(r"\bо\b", "", remaining, flags=re.IGNORECASE)
        remaining = re.sub(r"\bоб\b", "", remaining, flags=re.IGNORECASE)
        remaining = re.sub(r"\bпо\s+теме\b", "", remaining, flags=re.IGNORECASE)
        remaining = re.sub(r"\bна\s+тему\b", "", remaining, flags=re.IGNORECASE)
        remaining = re.sub(r"\bчто\s+нового\b", "", remaining, flags=re.IGNORECASE)
        remaining = re.sub(r"\bновости\b", "", remaining, flags=re.IGNORECASE)

        remaining = re.sub(r"\s+", " ", remaining).strip()

        if remaining:
            topic = remaining

    return ParsedQuery(
        start_date=start_date,
        end_date=end_date,
        topic=topic
    )


def calculate_scroll_depth(target_date: date) -> int:
    today = date.today()
    days_ago = (today - target_date).days

    if days_ago <= 0:
        return 5
    elif days_ago == 1:
        return 10
    elif days_ago <= 3:
        return 20
    elif days_ago <= 7:
        return 40
    elif days_ago <= 14:
        return 60
    elif days_ago <= 30:
        return 80
    else:
        return 100


def format_date_range(start_date: date, end_date: date) -> str:
    today = date.today()
    yesterday = today - timedelta(days=1)

    if start_date == end_date:
        if start_date == today:
            return "сегодня"
        elif start_date == yesterday:
            return "вчера"
        else:
            return start_date.strftime("%d.%m.%Y")
    else:
        days = (end_date - start_date).days + 1
        return f"за последние {days} дней"
