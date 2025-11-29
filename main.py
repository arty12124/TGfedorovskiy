import os
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
import re
import asyncio
import aiosqlite
import pytz
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional

from urllib.parse import quote as urlquote
import httpx
from bs4 import BeautifulSoup

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties

# ===================== CONFIG =====================
WELCOME_IMAGE_URL = "https://sun9-7.userapi.com/s/v1/ig2/63zp3aqiX6cZGx-Aal4ltfGvqLq7RIQlBemYcUfHrEH2lpEQCQgOMWRv6_HsRqpzGJPph-a-TWSyuc4b_pk8-YZ3.jpg?quality=95&as=32x12,48x18,72x27,108x41,160x61,240x91,360x137,480x183,540x205,640x244,720x274,1080x411,1280x487,1440x548,1640x624&from=bu&cs=1640x0"

# НГТУ (Новосибирск)
TZ = pytz.timezone("Asia/Novosibirsk")

# Ссылки расписаний
SCHEDULE_ROOT = "https://www.nstu.ru/studies/schedule/schedule_classes"
GROUP_URL = "https://www.nstu.ru/studies/schedule/schedule_classes/schedule?group={group}&print=true"
GROUP_URL_FALLBACK = "https://xn--c1atqe.xn--p1ai/studies/schedule/schedule_classes/schedule?group={group}&print=true"

# Значения по умолчанию
DEFAULT_LANG = "ru"
DEFAULT_ADVANCE_MIN = 10
PAGE_SIZE = 20
DB_PATH = "bot.db"
# ==================================================

bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
rt = Router()
dp.include_router(rt)

# --------- локализация ---------
T = {
    "ru": {
        "welcome_title": "Привет! Мы команда <b>Fedorovskiy</b> 👋",
        "welcome_body": "Мы пришлем тебе напоминание <b>за {m} минут</b> до начала пары: предмет, корпус, аудитория и этаж.\nВыбери свою группу!",
        "btn_pick": "🎓 Выбрать группу",
        "btn_profile": "👤 Личный кабинет",
        "btn_settings": "⚙️ Настройки",
        "btn_donate": "❤️ Донат",

        "profile_title": "👤 Личный кабинет",
        "profile_name": "Имя: <b>{name}</b>",
        "profile_group": "Группа: <b>{group}</b>",

        "pick_prompt": "Найдено групп: <b>{n}</b>. Выбери свою:",
        "not_found": "Ничего не нашёл. Попробуй точнее (например: <b>ПМИ-52</b>).",
        "cant_load_list": "Не удалось получить список групп. Попробуй поиск по подстроке, например: <b>ПМИ</b>.",
        "group_set": "Группа установлена: <b>{g}</b> ✅\nТеперь буду писать за {m} минут до начала каждой пары.",

        "notify_soon": "Через <b>{m} мин</b> начинается пара:",
        "time_line": "🕘 <b>{start}-{end}</b> ({date})",
        "subject": "📚 {s}",
        "place": "📍 {text}",

        "settings_title": "⚙️ Настройки",
        "settings_curr": "Текущий язык: <b>{lang}</b>\nИнтервал напоминаний: <b>{m} мин</b>",
        "settings_lang_title": "🌐 Язык",
        "settings_adv_title": "⏰ Периодичность напоминаний",

        "btn_lang_menu": "🌐 Язык",
        "btn_adv_menu": "⏰ Периодичность",

        "btn_lang_ru": "🇷🇺 Русский",
        "btn_lang_en": "🇬🇧 English",

        "btn_adv_5": "⏰ 5 мин",
        "btn_adv_10": "⏰ 10 мин",
        "btn_adv_15": "⏰ 15 мин",
        "btn_adv_20": "⏰ 20 мин",
        "btn_adv_30": "⏰ 30 мин",

        "saved": "Сохранено ✅",
        "donate": "Если хочешь поддержать развитие — спасибо! 🙏\n<b>Донат:</b> https://donate.example",
        "ping": "бот активен ✅",
        "faculties_prompt": "🏫 Выберите факультет:",
        "fac_prompt": "📋 Факультет {fac}. Найдено групп: <b>{n}</b>. Выберите группу:",
        "show_all": {"показать все", "все", "список"},
    },
    "en": {
        "welcome_title": "Hi! We are <b>Fedorovskiy</b> team 👋",
        "welcome_body": "I'll notify you <b>{m} minutes</b> before classes: subject, building, room and floor.\nPick your group to start!",
        "btn_pick": "🎓 Choose group",
        "btn_profile": "👤 Profile",
        "btn_settings": "⚙️ Settings",
        "btn_donate": "❤️ Donate",

        "profile_title": "👤 Profile",
        "profile_name": "Name: <b>{name}</b>",
        "profile_group": "Group: <b>{group}</b>",

        "pick_prompt": "Found groups: <b>{n}</b>. Choose yours:",
        "not_found": "Nothing found. Try more precise (e.g. <b>PMI-52</b>).",
        "cant_load_list": "Couldn't fetch list. Try typing a substring, e.g. <b>PMI</b>.",
        "group_set": "Group set: <b>{g}</b> ✅\nI'll message {m} minutes before each class.",

        "notify_soon": "In <b>{m} min</b> your class will start:",
        "time_line": "🕘 <b>{start}-{end}</b> ({date})",
        "subject": "📚 {s}",
        "place": "📍 {text}",

        "settings_title": "⚙️ Settings",
        "settings_curr": "Current language: <b>{lang}</b>\nReminder: <b>{m} min</b>",
        "settings_lang_title": "🌐 Language",
        "settings_adv_title": "⏰ Reminder lead time",

        "btn_lang_menu": "🌐 Language",
        "btn_adv_menu": "⏰ Reminder",

        "btn_lang_ru": "🇷🇺 Русский",
        "btn_lang_en": "🇬🇧 English",

        "btn_adv_5": "⏰ 5 min",
        "btn_adv_10": "⏰ 10 min",
        "btn_adv_15": "⏰ 15 min",
        "btn_adv_20": "⏰ 20 min",
        "btn_adv_30": "⏰ 30 min",

        "saved": "Saved ✅",
        "donate": "Support the project — thanks! 🙏\n<b>Donate:</b> https://donate.example",
        "ping": "bot is alive ✅",
        "faculties_prompt": "🏫 Choose a faculty:",
        "fac_prompt": "📋 Faculty {fac}. Groups found: <b>{n}</b>. Choose your group:",
        "show_all": {"show all", "all", "list", "показать все", "все", "список"},
    }
}

faculty_groups_map: Dict[str, List[str]] = {}

FACULTY_SITES = [
    ("AVTF", "АВТФ", "https://avtf.nstu.ru/study_process/schedule/schedule_classes"),
    ("MTF", "МТФ", "https://www.mtf.nstu.ru/study_process/schedule/schedule_classes"),
    ("REF", "РЭФ", "https://www.ref.nstu.ru/study_process/schedule/schedule_classes"),
    ("FB", "ФБ", "https://www.fb.nstu.ru/study_process/schedule/schedule_classes"),
    ("FGO", "ФГО", "https://www.fgo.nstu.ru/study_process/schedule/schedule_classes"),
    ("FLA", "ФЛА", "https://fla.nstu.ru/study_process/schedule/schedule_classes"),
    ("FPMI", "ФПМИ", "https://fpmi.nstu.ru/study_process/schedule/schedule_classes"),
    ("FTF", "ФТФ", "https://www.ftf.nstu.ru/study_process/schedule/schedule_classes"),
    ("FEN", "ФЭН", "https://fen.nstu.ru/study_process/schedule/schedule_classes"),
]

FACULTY_ORDER = ["АВТФ", "МТФ", "РЭФ", "ФБ", "ФГО", "ФЛА", "ФПМИ", "ФТФ", "ФЭН"]
RU_TO_KEY = {ru: key for key, ru, url in FACULTY_SITES}
FACULTY_ORDER_KEYS = [RU_TO_KEY[ru] for ru in FACULTY_ORDER if ru in RU_TO_KEY]

# ----------------- БД -----------------
CREATE_SQL = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY,
  group_code TEXT,
  lang TEXT NOT NULL DEFAULT 'ru',
  advance_min INTEGER NOT NULL DEFAULT 10
);
CREATE TABLE IF NOT EXISTS sent_notifications (
  user_id INTEGER NOT NULL,
  pair_date TEXT NOT NULL,
  pair_start TEXT NOT NULL,
  UNIQUE(user_id, pair_date, pair_start)
);
CREATE TABLE IF NOT EXISTS groups_cache (
  group_code TEXT PRIMARY KEY,
  valid INTEGER NOT NULL
);
"""

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_SQL)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN lang TEXT NOT NULL DEFAULT 'ru'")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN advance_min INTEGER NOT NULL DEFAULT 10")
        except Exception:
            pass
        await db.commit()

async def get_user(user_id: int) -> Dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT group_code, lang, advance_min FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        if row:
            return {"group": row[0], "lang": row[1], "advance": int(row[2])}
        await db.execute("INSERT OR IGNORE INTO users(user_id, group_code, lang, advance_min) VALUES(?,?,?,?)",
                         (user_id, None, DEFAULT_LANG, DEFAULT_ADVANCE_MIN))
        await db.commit()
    return {"group": None, "lang": DEFAULT_LANG, "advance": DEFAULT_ADVANCE_MIN}

async def set_user_group(user_id: int, group_code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id, group_code, lang, advance_min) VALUES(?,?,?,?)",
                         (user_id, group_code, DEFAULT_LANG, DEFAULT_ADVANCE_MIN))
        await db.execute("UPDATE users SET group_code=? WHERE user_id=?", (group_code, user_id))
        await db.commit()

async def set_user_lang(user_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, user_id))
        await db.commit()

async def set_user_advance(user_id: int, minutes: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET advance_min=? WHERE user_id=?", (minutes, user_id))
        await db.commit()

async def mark_sent(user_id: int, d: date, start_hhmm: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO sent_notifications(user_id, pair_date, pair_start) VALUES(?,?,?)",
            (user_id, d.isoformat(), start_hhmm)
        )
        await db.commit()

async def is_sent(user_id: int, d: date, start_hhmm: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM sent_notifications WHERE user_id=? AND pair_date=? AND pair_start=?",
            (user_id, d.isoformat(), start_hhmm)
        )
        return await cur.fetchone() is not None

# ----------------- HTTP -----------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NSTUNotifyBot/1.0)",
    "Accept-Language": "ru,en;q=0.9",
}

async def fetch(url: str, *, timeout: int = 20) -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, headers=HEADERS, verify=True) as client:
        r = await client.get(url)
        if r.status_code == 403 and "nstu.ru" in url:
            alt = url.replace("www.nstu.ru", "xn--c1atqe.xn--p1ai")
            r = await client.get(alt)
        r.raise_for_status()
        return r.text

# ----------------- Группы (жёсткий парсер) -----------------
# Кандидаты строго «Буквы[-]Цифры[доп.буквы/цифры/тире]», без пробелов.
CANDIDATE_RE = re.compile(
    r'\b[А-ЯA-ZЁ][А-ЯA-ZЁ\-]{0,10}-?\d{1,4}[А-ЯA-ZЁ0-9\-]{0,6}\b',
    flags=re.IGNORECASE
)
VALID_GROUP_RE = re.compile(r'^[А-ЯA-ZЁ][А-ЯA-ZЁ\-]*\d+[А-ЯA-ZЁ0-9\-]*$')

def normalize_token(s: str) -> str:
    return (s or "").replace('\u00A0', ' ').strip().upper()

def is_valid_group(token: str) -> bool:
    token = normalize_token(token)
    if not token:
        return False
    if ' ' in token:
        return False
    # отсекаем «800 222 …» и прочие чисто цифровые/телефонные
    if token.replace('-', '').isdigit():
        return False
    return bool(VALID_GROUP_RE.match(token))

async def purge_invalid_groups():
    """Удалить из кеша всё, что не похоже на корректный код группы."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT group_code FROM groups_cache")
        rows = await cur.fetchall()
        bad = [r[0] for r in rows if not is_valid_group(r[0])]
        if bad:
            await db.executemany("DELETE FROM groups_cache WHERE group_code=?", [(g,) for g in bad])
            await db.commit()

async def crawl_groups() -> Dict[str, List[str]]:
    global faculty_groups_map
    faculty_groups_map = {}
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM groups_cache")
        await db.commit()
        for fac_key, fac_name_ru, url in FACULTY_SITES:
            try:
                html = await fetch(url)
            except Exception:
                continue
            soup = BeautifulSoup(html, "lxml")
            text = soup.get_text(" ", strip=True)

            raw = set(CANDIDATE_RE.findall(text))
            codes: set[str] = set()
            for tok in raw:
                tok = normalize_token(tok)
                if is_valid_group(tok):
                    codes.add(tok)

            sorted_codes = sorted(codes)
            faculty_groups_map[fac_key] = sorted_codes
            for g in sorted_codes:
                await db.execute("INSERT OR REPLACE INTO groups_cache(group_code, valid) VALUES(?, 1)", (g,))
        await db.commit()
    await purge_invalid_groups()
    return faculty_groups_map

async def search_groups(substr: str, limit: int = 200) -> List[str]:
    q = normalize_token(substr)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT group_code FROM groups_cache WHERE valid=1 AND UPPER(group_code) LIKE ?",
            (f"%{q}%",)
        )
        rows = await cur.fetchall()
    groups = [normalize_token(r[0]) for r in rows if is_valid_group(r[0])]
    return sorted(groups)[:limit]

# ----------------- Парсинг занятий -----------------
TIME_SLOT_RE = re.compile(r'(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})')

def to_local_dt(d: date, hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return TZ.localize(datetime(d.year, d.month, d.day, h, m))

def parse_floor(room: str) -> Optional[int]:
    m = re.search(r"-\s*([0-9]{3,4})", room)
    if not m:
        m2 = re.search(r"-\s*([0-9]{2})", room)
        if m2:
            n = m2.group(1)
            return int(n[0])
        return None
    num = m.group(1)
    try:
        return int(num[0])
    except Exception:
        return None

def parse_building(room: str) -> Optional[str]:
    m = re.match(r"\s*([0-9]+)\s*-\s*", room)
    return m.group(1) if m else None

async def fetch_group_schedule_html(group_code: str) -> str:
    url = GROUP_URL.format(group=urlquote(group_code))
    return await fetch(url)

def russian_weekday_index(dt: date) -> int:
    return dt.weekday()

def extract_today_pairs(html: str, target_date: date) -> List[Dict]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return []
    rows = table.find_all("tr")
    if not rows:
        return []
    day_idx = russian_weekday_index(target_date) + 1  # 0-й столбец — время

    pairs = []
    for r in rows[1:]:
        cells = r.find_all(["td", "th"])
        if len(cells) <= day_idx:
            continue
        time_cell = cells[0].get_text(" ", strip=True)
        day_cell = cells[day_idx]
        m = TIME_SLOT_RE.search(time_cell)
        if not m:
            continue
        start, end = m.groups()
        cell_text = day_cell.get_text(" ", strip=True)
        if not cell_text:
            continue

        room_match = re.search(r"\b[1-9]-\s*[0-9A-Za-zА-Яа-я\-]{2,6}\b", cell_text)
        room = room_match.group(0).replace(" ", "") if room_match else ""
        building = parse_building(room) if room else None
        floor = parse_floor(room) if room else None

        subject = cell_text
        if room:
            subject = subject.replace(room, "").strip()
        subject = re.sub(r"\s{2,}", " ", subject)

        pairs.append({
            "start": start,
            "end": end,
            "subject": subject,
            "room": room,
            "building": building,
            "floor": floor
        })
    return pairs

# ----------------- Нотификации -----------------
async def notify_loop():
    await asyncio.sleep(2)
    while True:
        try:
            now = datetime.now(TZ)
            today = now.date()

            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute("SELECT user_id, group_code, advance_min FROM users WHERE group_code IS NOT NULL")
                users = await cur.fetchall()

            group_html_cache: Dict[str, str] = {}
            for user_id, group_code, adv in users:
                if group_code not in group_html_cache:
                    try:
                        html = await fetch_group_schedule_html(group_code)
                        group_html_cache[group_code] = html
                    except Exception:
                        continue
                html = group_html_cache[group_code]
                pairs = extract_today_pairs(html, today)
                if not pairs:
                    continue

                for p in pairs:
                    start_dt = to_local_dt(today, p["start"])
                    notify_moment = start_dt - timedelta(minutes=int(adv))
                    if notify_moment <= now < notify_moment + timedelta(minutes=1):
                        if not await is_sent(user_id, today, p["start"]):
                            u = await get_user(user_id)
                            lang = u["lang"]
                            text = build_notification_text(lang, int(adv), p, today)
                            try:
                                await bot.send_message(user_id, text)
                                await mark_sent(user_id, today, p["start"])
                            except Exception:
                                pass

            if now.hour == 3 and now.minute == 0:
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute("DELETE FROM sent_notifications WHERE pair_date < ?", ((today).isoformat(),))
                    await db.commit()
        except Exception:
            pass
        await asyncio.sleep(60)

def build_notification_text(lang: str, minutes: int, p: Dict, d: date) -> str:
    t = T.get(lang, T["ru"])
    parts = [t["notify_soon"].format(m=minutes)]
    parts.append(t["time_line"].format(start=p['start'], end=p['end'], date=d.strftime('%d.%m.%Y')))
    if p.get("subject"):
        parts.append(t["subject"].format(s=p['subject']))
    loc_bits = []
    if p.get("building"):
        loc_bits.append(f"корпус {p['building']}")
    if p.get("room"):
        loc_bits.append(f"ауд. {p['room'].split('-', 1)[-1]}")
    if p.get("floor"):
        loc_bits.append(f"{p['floor']} этаж")
    if loc_bits:
        parts.append(t["place"].format(text=", ".join(loc_bits)))
    return "\n".join(parts)

# ----------------- Вспомогательное: пагинация -----------------
def pagination_row(prefix: str, page: int, total_pages: int) -> List[InlineKeyboardButton]:
    # всегда три кнопки: «   N/M   »
    left_cb = f"{prefix}:{page-1}" if page > 0 else "noop"
    right_cb = f"{prefix}:{page+1}" if page < total_pages - 1 else "noop"
    return [
        InlineKeyboardButton(text="«", callback_data=left_cb),
        InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"),
        InlineKeyboardButton(text="»", callback_data=right_cb),
    ]

def pagination_row_fac(prefix: str, fac: str, page: int, total_pages: int) -> List[InlineKeyboardButton]:
    left_cb = f"{prefix}:{fac}:{page-1}" if page > 0 else "noop"
    right_cb = f"{prefix}:{fac}:{page+1}" if page < total_pages - 1 else "noop"
    return [
        InlineKeyboardButton(text="«", callback_data=left_cb),
        InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"),
        InlineKeyboardButton(text="»", callback_data=right_cb),
    ]

# ----------------- Клавиатуры -----------------
def main_menu_kb(lang: str):
    t = T.get(lang, T["ru"])
    kb = InlineKeyboardBuilder()
    kb.button(text=t["btn_pick"], callback_data="menu:pick")
    kb.button(text=t["btn_profile"], callback_data="menu:profile")
    kb.button(text=t["btn_settings"], callback_data="menu:settings")
    kb.button(text=t["btn_donate"], callback_data="menu:donate")
    kb.adjust(1)
    return kb.as_markup()


def settings_root_kb(lang: str):
    t = T.get(lang, T["ru"])
    back_text = "◀️ Назад" if lang == "ru" else "◀️ Back"
    rows = [
        [InlineKeyboardButton(text=t["btn_lang_menu"], callback_data="settings:lang")],
        [InlineKeyboardButton(text=t["btn_adv_menu"], callback_data="settings:adv")],
        [InlineKeyboardButton(text=back_text, callback_data="back:main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_lang_kb(lang: str):
    t = T.get(lang, T["ru"])
    back_text = "◀️ Назад" if lang == "ru" else "◀️ Back"
    rows = [
        [InlineKeyboardButton(text=t["btn_lang_ru"], callback_data="set:lang:ru")],
        [InlineKeyboardButton(text=t["btn_lang_en"], callback_data="set:lang:en")],
        [InlineKeyboardButton(text=back_text, callback_data="back:settings")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_adv_kb(lang: str):
    t = T.get(lang, T["ru"])
    back_text = "◀️ Назад" if lang == "ru" else "◀️ Back"
    rows = [
        [InlineKeyboardButton(text=t["btn_adv_5"], callback_data="set:adv:5")],
        [InlineKeyboardButton(text=t["btn_adv_10"], callback_data="set:adv:10")],
        [InlineKeyboardButton(text=t["btn_adv_15"], callback_data="set:adv:15")],
        [InlineKeyboardButton(text=t["btn_adv_20"], callback_data="set:adv:20")],
        [InlineKeyboardButton(text=t["btn_adv_30"], callback_data="set:adv:30")],
        [InlineKeyboardButton(text=back_text, callback_data="back:settings")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# --------- хелпер редактирования одного и того же сообщения ---------
async def edit_message(message: Message, text: str, markup: InlineKeyboardMarkup):
    """
    Меняем текст/подпись и клавиатуру в ТЕКУЩЕМ сообщении.
    Если это фото — меняем caption, если текст — меняем text.
    """
    try:
        if message.photo:
            await message.edit_caption(caption=text, reply_markup=markup)
        else:
            await message.edit_text(text=text, reply_markup=markup)
    except Exception:
        # На всякий случай, если редактирование не удалось — шлём новое текстовое сообщение
        await message.answer(text, reply_markup=markup)


# --------- билдеры экранов (текст + клавиатура), без отправки ---------
def build_faculty_picker(lang: str) -> tuple[str, InlineKeyboardMarkup]:
    t = T.get(lang, T["ru"])
    if not faculty_groups_map:
        # если ещё не загрузились – просто покажем заглушку, кнопка "Назад" всё равно работает
        back_text = "◀️ Назад" if lang == "ru" else "◀️ Back"
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=back_text, callback_data="back:main")]
            ]
        )
        return t["cant_load_list"], markup

    buttons: List[InlineKeyboardButton] = []
    for fac in FACULTY_ORDER_KEYS:
        name_ru = next((ru for key, ru, url in FACULTY_SITES if key == fac), fac)
        name_en = fac
        label = name_ru if lang == "ru" else name_en
        buttons.append(InlineKeyboardButton(text=label, callback_data=f"fac:{fac}"))

    rows: List[List[InlineKeyboardButton]] = []
    for i in range(0, len(buttons), 3):
        rows.append(buttons[i : i + 3])

    back_text = "◀️ Назад" if lang == "ru" else "◀️ Back"
    rows.append([InlineKeyboardButton(text=back_text, callback_data="back:main")])

    markup = InlineKeyboardMarkup(inline_keyboard=rows)
    return t["faculties_prompt"], markup


def build_group_picker_global(
    groups: List[str], page: int, lang: str
) -> tuple[str, InlineKeyboardMarkup]:
    """
    Список групп без факультета (поиск / все группы)
    """
    t = T.get(lang, T["ru"])
    total_pages = max(1, (len(groups) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    chunk = groups[start : start + PAGE_SIZE]

    rows: List[List[InlineKeyboardButton]] = []
    group_buttons = [
        InlineKeyboardButton(text=g, callback_data=f"pick:{g}") for g in chunk
    ]
    for i in range(0, len(group_buttons), 3):
        rows.append(group_buttons[i : i + 3])

    rows.append(pagination_row("page", page, total_pages))

    back_text = "◀️ Назад" if lang == "ru" else "◀️ Back"
    rows.append([InlineKeyboardButton(text=back_text, callback_data="back:main")])

    markup = InlineKeyboardMarkup(inline_keyboard=rows)
    text = t["pick_prompt"].format(n=len(groups))
    return text, markup


def build_group_picker_fac(
    groups: List[str], fac: str, page: int, lang: str
) -> tuple[str, InlineKeyboardMarkup]:
    """
    Список групп внутри конкретного факультета.
    """
    t = T.get(lang, T["ru"])
    total_pages = max(1, (len(groups) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    chunk = groups[start : start + PAGE_SIZE]

    rows: List[List[InlineKeyboardButton]] = []
    grp_buttons = [
        InlineKeyboardButton(text=g, callback_data=f"pick:{g}") for g in chunk
    ]
    for i in range(0, len(grp_buttons), 3):
        rows.append(grp_buttons[i : i + 3])

    rows.append(pagination_row_fac("page", fac, page, total_pages))

    back_text = "◀️ Назад" if lang == "ru" else "◀️ Back"
    rows.append([InlineKeyboardButton(text=back_text, callback_data="back:fac")])

    markup = InlineKeyboardMarkup(inline_keyboard=rows)
    fac_name = next((ru for key, ru, url in FACULTY_SITES if key == fac), fac)
    fac_display = fac_name if lang == "ru" else fac
    text = t["fac_prompt"].format(fac=fac_display, n=len(groups))
    return text, markup


# ----------------- Хендлеры: старт и текст -----------------
@rt.message(CommandStart())
async def start_cmd(m: Message):
    u = await get_user(m.from_user.id)
    t = T.get(u["lang"], T["ru"])
    caption = t["welcome_title"] + "\n\n" + t["welcome_body"].format(m=u["advance"])
    # стартовое сообщение – всегда новое с баннером
    try:
        await bot.send_photo(
            m.chat.id,
            WELCOME_IMAGE_URL,
            caption=caption,
            reply_markup=main_menu_kb(u["lang"]),
        )
    except Exception:
        await m.answer(caption, reply_markup=main_menu_kb(u["lang"]))


@rt.message(Command("ping"))
async def ping_cmd(m: Message):
    u = await get_user(m.from_user.id)
    await m.answer(T.get(u["lang"], T["ru"])["ping"])


@rt.message(F.text.regexp(r"^[\s\S]{1,40}$"))
async def handle_text(m: Message):
    # это ОТДЕЛЬНЫЙ случай – отвечаем новым сообщением,
    # потому что редактировать чужое (сообщение пользователя) нельзя
    u = await get_user(m.from_user.id)
    t = T.get(u["lang"], T["ru"])
    q = (m.text or "").strip()
    if not q:
        return

    # показать все факультеты
    if q.lower() in t["show_all"]:
        text, markup = build_faculty_picker(u["lang"])
        await m.answer(text, reply_markup=markup)
        return

    # поиск групп
    groups = await search_groups(q)
    if not groups:
        await m.answer(t["not_found"])
        return

    text, markup = build_group_picker_global(groups, page=0, lang=u["lang"])
    await m.answer(text, reply_markup=markup)


# ----------------- Личный кабинет -----------------
@rt.callback_query(F.data == "menu:profile")
async def profile_cb(c: CallbackQuery):
    u = await get_user(c.from_user.id)
    lang = u["lang"]
    t = T.get(lang, T["ru"])

    name = c.from_user.full_name or c.from_user.username or "-"
    group_disp = u["group"] if u["group"] else "❌"

    text = (
        f"{t['profile_title']}\n\n"
        f"{t['profile_name'].format(name=name)}\n"
        f"{t['profile_group'].format(group=group_disp)}"
    )

    back_text = "◀️ Назад" if lang == "ru" else "◀️ Back"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=back_text, callback_data="back:main")]]
    )

    await edit_message(c.message, text, kb)
    await c.answer()


# ----------------- Факультеты/группы -----------------
@rt.callback_query(F.data == "menu:pick")
async def cb_menu_pick(c: CallbackQuery):
    u = await get_user(c.from_user.id)
    # нажатие "Выбрать группу" – просто меняем текст и клавиатуру в ЭТОМ же сообщении
    if not faculty_groups_map:
        await crawl_groups()
    text, markup = build_faculty_picker(u["lang"])
    await edit_message(c.message, text, markup)
    await c.answer()


@rt.callback_query(F.data.startswith("fac:"))
async def faculty_cb(c: CallbackQuery):
    fac = c.data.split(":")[1]
    u = await get_user(c.from_user.id)
    lang = u["lang"]

    if fac not in faculty_groups_map:
        await crawl_groups()
    groups = faculty_groups_map.get(fac, [])
    if not groups:
        await c.answer(T.get(lang, T["ru"])["cant_load_list"], show_alert=True)
        return

    text, markup = build_group_picker_fac(groups, fac=fac, page=0, lang=lang)
    await edit_message(c.message, text, markup)
    await c.answer()


@rt.callback_query(F.data.startswith("page"))
async def page_cb(c: CallbackQuery):
    data = c.data
    parts = data.split(":")
    u = await get_user(c.from_user.id)
    lang = u["lang"]

    # Глобальная пагинация групп (без факультета)
    if len(parts) == 2:
        try:
            page = int(parts[1])
        except Exception:
            await c.answer()
            return

        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT group_code FROM groups_cache WHERE valid=1 ORDER BY group_code"
            )
            rows = await cur.fetchall()
        groups = [r[0] for r in rows if is_valid_group(r[0])]

        if not groups:
            await c.answer(T.get(lang, T["ru"])["cant_load_list"], show_alert=True)
            return

        text, markup = build_group_picker_global(groups, page=page, lang=lang)
        await edit_message(c.message, text, markup)

    # Пагинация внутри факультета
    elif len(parts) == 3:
        fac = parts[1]
        try:
            page = int(parts[2])
        except Exception:
            await c.answer()
            return

        if fac not in faculty_groups_map or not faculty_groups_map.get(fac):
            await crawl_groups()
        groups = faculty_groups_map.get(fac, [])
        if not groups:
            await c.answer(T.get(lang, T["ru"])["cant_load_list"], show_alert=True)
            return

        text, markup = build_group_picker_fac(groups, fac=fac, page=page, lang=lang)
        await edit_message(c.message, text, markup)

    await c.answer()


@rt.callback_query(F.data.startswith("pick:"))
async def pick_cb(c: CallbackQuery):
    group = c.data.split(":", 1)[1]
    u = await get_user(c.from_user.id)
    t = T.get(u["lang"], T["ru"])
    await set_user_group(c.from_user.id, group)

    text = t["group_set"].format(g=group, m=u["advance"])
    # после выбора группы просто показываем текст с подтверждением + назад в меню
    back_text = "◀️ В меню" if u["lang"] == "ru" else "◀️ Menu"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=back_text, callback_data="back:main")]]
    )
    await edit_message(c.message, text, kb)
    await c.answer()


@rt.callback_query(F.data == "noop")
async def noop_cb(c: CallbackQuery):
    await c.answer()


# ---------- настройки ----------
async def send_settings(c: CallbackQuery, lang: str, adv: int):
    t = T.get(lang, T["ru"])
    text = (
        f"{t['settings_title']}\n\n"
        + t["settings_curr"].format(
            lang=("Русский" if lang == "ru" else "English"), m=adv
        )
    )
    await edit_message(c.message, text, settings_root_kb(lang))
    await c.answer()


@rt.callback_query(F.data == "menu:settings")
async def cb_menu_settings(c: CallbackQuery):
    u = await get_user(c.from_user.id)
    await send_settings(c, u["lang"], u["advance"])


@rt.callback_query(F.data == "settings:lang")
async def settings_lang_menu(c: CallbackQuery):
    u = await get_user(c.from_user.id)
    lang = u["lang"]
    t = T.get(lang, T["ru"])
    await edit_message(c.message, t["settings_lang_title"], settings_lang_kb(lang))
    await c.answer()


@rt.callback_query(F.data == "settings:adv")
async def settings_adv_menu(c: CallbackQuery):
    u = await get_user(c.from_user.id)
    lang = u["lang"]
    t = T.get(lang, T["ru"])
    await edit_message(c.message, t["settings_adv_title"], settings_adv_kb(lang))
    await c.answer()


@rt.callback_query(F.data.startswith("set:lang:"))
async def set_lang_cb(c: CallbackQuery):
    lang = c.data.split(":")[-1]
    await set_user_lang(c.from_user.id, lang)
    u = await get_user(c.from_user.id)

    await edit_message(c.message, T.get(lang, T["ru"])["saved"], settings_root_kb(lang))
    # после «Сохранено» сразу же показать экраны настроек
    await send_settings(c, u["lang"], u["advance"])


@rt.callback_query(F.data.startswith("set:adv:"))
async def set_adv_cb(c: CallbackQuery):
    minutes = int(c.data.split(":")[-1])
    await set_user_advance(c.from_user.id, minutes)
    u = await get_user(c.from_user.id)

    await edit_message(
        c.message, T.get(u["lang"], T["ru"])["saved"], settings_root_kb(u["lang"])
    )
    await send_settings(c, u["lang"], u["advance"])


@rt.callback_query(F.data == "back:settings")
async def back_settings_cb(c: CallbackQuery):
    u = await get_user(c.from_user.id)
    await send_settings(c, u["lang"], u["advance"])


# ---------- донат ----------
@rt.callback_query(F.data == "menu:donate")
async def cb_menu_donate(c: CallbackQuery):
    u = await get_user(c.from_user.id)
    lang = u["lang"]
    back_text = "◀️ Назад" if lang == "ru" else "◀️ Back"
    markup = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=back_text, callback_data="back:main")]]
    )
    await edit_message(c.message, T.get(lang, T["ru"])["donate"], markup)
    await c.answer()


# ---------- назад ----------
@rt.callback_query(F.data == "back:fac")
async def back_fac_cb(c: CallbackQuery):
    u = await get_user(c.from_user.id)
    text, markup = build_faculty_picker(u["lang"])
    await edit_message(c.message, text, markup)
    await c.answer()


@rt.callback_query(F.data == "back:main")
async def back_main_cb(c: CallbackQuery):
    u = await get_user(c.from_user.id)
    t = T.get(u["lang"], T["ru"])
    caption = t["welcome_title"] + "\n\n" + t["welcome_body"].format(m=u["advance"])

    # просто меняем текст/подпись и клавиатуру в ЭТОМ же сообщении
    await edit_message(c.message, caption, main_menu_kb(u["lang"]))
    await c.answer()


# ----------------- main -----------------
async def main():
    await init_db()
    asyncio.create_task(crawl_groups())
    asyncio.create_task(notify_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass






from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.types import Update

bot = Bot(TOKEN)
dp = Dispatcher()

# --- твои хендлеры остаются как есть ---
# router.use(...) если есть router
# dp.include_router(router) в конце

# обработчик webhook
async def handle_webhook(request: web.Request):
    data = await request.json()
    update = Update(**data)
    await dp.process_update(update)
    return web.Response(text="ok")

async def on_startup(app):
    # Render создаёт переменную с публичным URL
    service_url = os.getenv("RENDER_EXTERNAL_URL")
    webhook_url = f"{service_url}/webhook/{TOKEN}"

    await bot.set_webhook(webhook_url)
    print("Webhook set:", webhook_url)

async def on_shutdown(app):
    await bot.delete_webhook()
    await bot.session.close()

def create_app():
    app = web.Application()
    app.router.add_post(f"/webhook/{TOKEN}", handle_webhook)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app

app = create_app()

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000))_





