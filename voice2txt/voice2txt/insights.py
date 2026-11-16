"""洞察統計：純函式，無 UI、無 I/O。"""
import re
from datetime import date, datetime, timedelta

# 打字速度假設：每分鐘 40 字（Typeless 洞察使用的保守基準），可由 compute(typing_wpm=) 覆寫。
TYPING_WPM = 40
WINDOW_DAYS = 182

_CJK = re.compile('[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')
_WORD = re.compile(r"[A-Za-z0-9]+(?:['\u2019][A-Za-z]+)*")


def count_words(text):
    """字數 = CJK 字元數 + 拉丁/數字詞數（don't 算 1 詞）。"""
    if not text:
        return 0
    return len(_CJK.findall(text)) + len(_WORD.findall(text))


def _to_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value)[:10], '%Y-%m-%d').date()


def _streaks(active, today):
    """active: set of date。回傳 (current, longest)；今天尚未活躍時從昨天往回算。"""
    if not active:
        return 0, 0
    longest = run = 0
    prev = None
    for d in sorted(active):
        run = run + 1 if prev is not None and d - prev == timedelta(days=1) else 1
        longest = max(longest, run)
        prev = d
    day = today if today in active else today - timedelta(days=1)
    current = 0
    while day in active:
        current += 1
        day -= timedelta(days=1)
    return current, longest


def compute(rows, today, typing_wpm=TYPING_WPM):
    """rows: (created, mode, seconds, text)。today: date。"""
    today = _to_date(today)
    total_words = 0
    total_seconds = 0.0
    per_day = {}
    by_mode = {}
    for created, mode, seconds, text in rows:
        words = count_words(text)
        total_words += words
        total_seconds += float(seconds or 0)
        day = _to_date(created)
        per_day[day] = per_day.get(day, 0) + words
        by_mode[mode] = by_mode.get(mode, 0) + words
    active = {d for d, w in per_day.items() if w > 0}
    current, longest = _streaks(active, today)
    start = today - timedelta(days=WINDOW_DAYS - 1)
    by_day = {d.isoformat(): w for d, w in sorted(per_day.items()) if start <= d <= today}
    wpm = total_words / (total_seconds / 60.0) if total_seconds > 0 else 0
    saved = max(0.0, total_words / float(typing_wpm) * 60.0 - total_seconds)
    return {'total_words': total_words, 'total_seconds': total_seconds,
            'dictation_wpm': wpm, 'active_days': len(active),
            'current_streak': current, 'longest_streak': longest,
            'time_saved_seconds': saved, 'by_day': by_day, 'by_mode': by_mode}


def heatmap_cells(by_day, today, weeks=26):
    """回傳 [(column, row, date_iso, words, level)]。row 0=週一；最後一欄含今天；未來日不輸出。
    level 0 = 無字數；1–4 依非零日的四分位。"""
    today = _to_date(today)
    monday = today - timedelta(days=today.weekday())
    first = monday - timedelta(weeks=weeks - 1)
    values = sorted(w for w in by_day.values() if w > 0)
    n = len(values)
    cuts = [values[max(0, (n * k) // 4 - 1)] for k in (1, 2, 3)] if n else []
    cells = []
    for col in range(weeks):
        for row in range(7):
            d = first + timedelta(days=col * 7 + row)
            if d > today:
                continue
            words = by_day.get(d.isoformat(), 0)
            level = 0 if words <= 0 else 1 + sum(words > c for c in cuts)
            cells.append((col, row, d.isoformat(), words, level))
    return cells
