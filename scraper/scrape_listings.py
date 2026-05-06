import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv
import requests
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "listings.json"

CONTACT_TEXT_PREFIX = "Qo'ng'iroq qilish"
CONTACT_URL_RE = re.compile(r"/MaklersizTopbot\?start=phone_\d+", re.I)

load_dotenv()

API_ID = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")
CHANNEL = os.getenv("TG_CHANNEL", "")
CONTACT_BOT = os.getenv("TG_CONTACT_BOT", "")
SINCE_DATE = os.getenv("SINCE_DATE", "2024-04-01")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "")
YANDEX_RPS = float(os.getenv("YANDEX_RPS", "5"))
YANDEX_CITY = os.getenv("YANDEX_CITY", "Tashkent, Uzbekistan")
USE_YANDEX = bool(YANDEX_API_KEY)
YANDEX_LOCK = asyncio.Lock()
YANDEX_LAST_CALL = 0.0
YANDEX_CACHE = {}

PHONE_RE = re.compile(r"\+?998\d{9}")
OWNER_RE = re.compile(r"@\w+")
PRICE_RE = re.compile(
    r"(?:narx|narxi|price|cena|цена)\s*[:\-]?\s*(\d{2,6})",
    re.I,
)
ROOMS_RE = re.compile(r"(\d+)\s*(?:xona|xonalik|komn|комн|rooms)", re.I)
FLOOR_RE = re.compile(r"(\d+)\s*/\s*(\d+)")
FLOOR_WORD_RE = re.compile(r"(\d+)\s*-?\s*qavat", re.I)
TOTAL_FLOORS_RE = re.compile(r"(\d+)\s*qavatl", re.I)
AREA_RE = re.compile(r"(\d+(?:[\.,]\d+)?)\s*(?:kv\.m|m2|m²|м2|м²|кв\.м)", re.I)
DISTRICT_RE = re.compile(r"(?:tuman|район)\s*[:\-]?\s*([^\n]+)", re.I)
ADDRESS_RE = re.compile(r"(?:manzil|address|адрес)\s*[:\-]?\s*([^\n]+)", re.I)
NEGOTIABLE_RE = re.compile(r"(kelishiladi|договор|negotiable)", re.I)
UZB_FIELD_RE = re.compile(r"^(?P<label>[\u2600-\u27BF\u1F300-\u1FAFF\w\s'ʻ‘’“”\-]+):\s*(?P<value>.+)$")
UZB_PRICE_INLINE_RE = re.compile(r"(\d+[\s\-]?(?:ming|mln|m|\$|usd|som|so'm))", re.I)
GIRL_HINTS = ("qiz", "qizlar", "qizlarga")
BOY_HINTS = ("o'g'il", "ogil", "o'gʻil", "o'g'il", "bola", "bollar", "bollarga", "yigit")
FAMILY_HINTS = ("oila", "oilaga", "oilaviy")
MANZIL_KEYS = ("manzil", "manzili")
MOLJAL_KEYS = ("mo'ljal", "moʻljal")
KIMLARGA_KEYS = ("kimlarga",)
XONALARI_KEYS = ("xonalar", "xonalari")


def parse_bot_url(url: str):
    if not url:
        return None

    if url.startswith("tg://"):
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        bot = params.get("domain", [None])[0]
        start_param = params.get("start", [None])[0]
        return bot, start_param

    parsed = urlparse(url)
    if "t.me" not in parsed.netloc:
        return None

    path = parsed.path.strip("/")
    if not path:
        return None

    bot = path.split("/")[0]
    params = parse_qs(parsed.query)
    start_param = params.get("start", [None])[0]
    return bot, start_param


def normalize_bot_username(raw: str):
    if not raw:
        return ""

    parsed = parse_bot_url(raw)
    if parsed:
        return parsed[0] or ""

    return raw.lstrip("@").strip()


def parse_contact_from_text(text: str):
    if not text:
        return None, None

    phone = PHONE_RE.search(text)
    owner = OWNER_RE.search(text)

    return phone.group(0) if phone else None, owner.group(0) if owner else None


def normalize_label(value: str):
    if not value:
        return ""

    normalized = value.lower()
    return (
        normalized.replace("ʻ", "'")
        .replace("’", "'")
        .replace("`", "'")
        .strip()
    )


def normalize_text(value: str):
    if not value:
        return ""

    normalized = value.lower()
    normalized = normalized.replace("ʻ", "'").replace("’", "'").replace("`", "'")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def clean_address(value: str):
    if not value:
        return None
    cleaned = value.strip()
    if cleaned.lower().startswith("i:"):
        cleaned = cleaned[2:].strip()
    return cleaned or None


def build_geocode_query(address: str, district: str | None):
    parts = [address, district, YANDEX_CITY]
    return ", ".join(part for part in parts if part)


def geocode_sync(query: str):
    url = "https://geocode-maps.yandex.ru/1.x/"
    params = {
        "apikey": YANDEX_API_KEY,
        "geocode": query,
        "format": "json",
        "lang": "uz_UZ",
        "results": 1,
    }
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    payload = response.json()
    members = (
        payload.get("response", {})
        .get("GeoObjectCollection", {})
        .get("featureMember", [])
    )
    if not members:
        return None, None
    pos = members[0].get("GeoObject", {}).get("Point", {}).get("pos", "")
    if not pos:
        return None, None
    lon_str, lat_str = pos.split()
    return float(lon_str), float(lat_str)


async def geocode_address(address: str | None, district: str | None):
    if not USE_YANDEX or not address:
        return None, None

    query = build_geocode_query(address, district)
    cache_key = normalize_text(query)
    if cache_key in YANDEX_CACHE:
        return YANDEX_CACHE[cache_key]

    min_interval = 1.0 / max(YANDEX_RPS, 1.0)
    async with YANDEX_LOCK:
        global YANDEX_LAST_CALL
        now = time.monotonic()
        wait_for = YANDEX_LAST_CALL + min_interval - now
        if wait_for > 0:
            await asyncio.sleep(wait_for)
        try:
            result = await asyncio.to_thread(geocode_sync, query)
        except Exception as exc:
            print(f"Geocoding failed for '{query}': {exc}")
            result = (None, None)
        YANDEX_LAST_CALL = time.monotonic()

    YANDEX_CACHE[cache_key] = result
    return result


def extract_listing_fields(text: str):
    if not text:
        return {}

    price = None
    rooms = None
    floor = None
    total_floors = None
    area = None
    district = None
    address = None
    price_negotiable = False
    for_boys = False
    for_girls = False
    for_families = False
    notes = None

    price_match = PRICE_RE.search(text)
    if price_match:
        price = int(price_match.group(1))
    else:
        for line in text.splitlines():
            match = UZB_FIELD_RE.match(line.strip())
            if not match:
                continue
            if "narx" in match.group("label").lower():
                inline_price = UZB_PRICE_INLINE_RE.search(match.group("value"))
                if inline_price:
                    price = parse_price_value(inline_price.group(1))
                break

    rooms_match = ROOMS_RE.search(text)
    if rooms_match:
        rooms = int(rooms_match.group(1))
    else:
        for line in text.splitlines():
            match = UZB_FIELD_RE.match(line.strip())
            if not match:
                continue
            if "xona" in match.group("label").lower():
                rooms_inline = ROOMS_RE.search(match.group("value"))
                if rooms_inline:
                    rooms = int(rooms_inline.group(1))
                break

    floor_match = FLOOR_RE.search(text)
    if floor_match:
        floor = int(floor_match.group(1))
        total_floors = int(floor_match.group(2))
    else:
        for line in text.splitlines():
            match = UZB_FIELD_RE.match(line.strip())
            if not match:
                continue
            if "xona" in match.group("label").lower():
                floor_inline = FLOOR_RE.search(match.group("value"))
                if floor_inline:
                    floor = int(floor_inline.group(1))
                    total_floors = int(floor_inline.group(2))
                break

    area_match = AREA_RE.search(text)
    if area_match:
        area = float(area_match.group(1).replace(",", "."))

    district_match = DISTRICT_RE.search(text)
    if district_match:
        district = district_match.group(1).strip()

    address_match = ADDRESS_RE.search(text)
    if address_match:
        address = address_match.group(1).strip()

    if NEGOTIABLE_RE.search(text):
        price_negotiable = True

    for line in text.splitlines():
        match = UZB_FIELD_RE.match(line.strip())
        if not match:
            continue

        label = normalize_label(match.group("label"))
        value = match.group("value").strip()

        if any(key in label for key in MANZIL_KEYS):
            if not address:
                address = value
        elif any(key in label for key in MOLJAL_KEYS):
            notes = value
        elif any(key in label for key in KIMLARGA_KEYS):
            value_norm = normalize_label(value)
            if any(hint in value_norm for hint in GIRL_HINTS):
                for_girls = True
            if any(hint in value_norm for hint in BOY_HINTS):
                for_boys = True
            if any(hint in value_norm for hint in FAMILY_HINTS):
                for_families = True
        elif any(key in label for key in XONALARI_KEYS):
            if rooms is None:
                rooms_inline = ROOMS_RE.search(value)
                if rooms_inline:
                    rooms = int(rooms_inline.group(1))

            if floor is None or total_floors is None:
                floor_pair = FLOOR_RE.search(value)
                if floor_pair:
                    floor = int(floor_pair.group(1))
                    total_floors = int(floor_pair.group(2))
                else:
                    total_match = TOTAL_FLOORS_RE.search(value)
                    floor_match = FLOOR_WORD_RE.search(value)
                    if floor_match and floor is None:
                        floor = int(floor_match.group(1))
                    if total_match and total_floors is None:
                        total_floors = int(total_match.group(1))

    return {
        "price": price,
        "price_negotiable": price_negotiable,
        "rooms": rooms,
        "floor": floor,
        "total_floors": total_floors,
        "area_sqm": area,
        "district": district,
        "address": clean_address(address),
        "for_boys": for_boys,
        "for_girls": for_girls,
        "for_families": for_families,
        "notes": notes,
    }


def parse_price_value(raw: str):
    if not raw:
        return None

    normalized = raw.lower().replace(" ", "")
    multiplier = 1
    if "ming" in normalized:
        multiplier = 1000
    elif "mln" in normalized or "m" in normalized:
        multiplier = 1_000_000

    digits = re.search(r"\d+", normalized)
    if not digits:
        return None

    return int(digits.group(0)) * multiplier


def build_dedupe_key(payload: dict):
    parts = [
        normalize_text(payload.get("address")),
        normalize_text(payload.get("district")),
        str(payload.get("rooms") or ""),
        str(payload.get("price") or ""),
        normalize_text(payload.get("contact_phone")),
    ]
    combined = "|".join(part for part in parts if part)
    return combined or None


def build_listing_payload(text: str, contact_phone: str, contact_owner: str, fields=None):
    if fields is None:
        fields = extract_listing_fields(text)
    description = text.strip() if text else None

    payload = {
        "owner_id": None,
        "lon": fields.get("lon"),
        "lat": fields.get("lat"),
        "address": fields.get("address"),
        "district": fields.get("district"),
        "price": fields.get("price"),
        "price_negotiable": fields.get("price_negotiable", False),
        "rooms": fields.get("rooms"),
        "floor": fields.get("floor"),
        "total_floors": fields.get("total_floors"),
        "area_sqm": fields.get("area_sqm"),
        "for_boys": fields.get("for_boys", False),
        "for_girls": fields.get("for_girls", False),
        "for_families": fields.get("for_families", False),
        "max_tenants": None,
        "needed_tenants": None,
        "utils_included": False,
        "has_wifi": False,
        "has_washing_machine": False,
        "has_fridge": False,
        "has_ac": False,
        "has_heating": False,
        "has_parking": False,
        "has_elevator": False,
        "has_furniture": False,
        "description": description,
        "notes": fields.get("notes"),
        "contact_phone": contact_phone,
        "contact_owner": contact_owner,
    }

    return payload


async def fetch_contact_from_button(client: TelegramClient, message):
    if not message.buttons:
        return None, None

    contact_button = None
    for row in message.buttons:
        for button in row:
            button_url = getattr(button, "url", "") or ""
            if CONTACT_URL_RE.search(button_url):
                contact_button = button
                break
        if contact_button:
            break

    if not contact_button:
        first_row = message.buttons[0] if message.buttons else None
        if not first_row:
            return None, None

        first_button = first_row[0] if first_row else None
        if not first_button:
            return None, None

        button_text = (first_button.text or "").strip()
        normalized_text = button_text.replace("ʻ", "'").replace("’", "'")
        if CONTACT_TEXT_PREFIX not in normalized_text:
            return None, None
        contact_button = first_button

    bot_username = normalize_bot_username(CONTACT_BOT)
    start_param = None

    button_url = getattr(contact_button, "url", None)
    if button_url:
        parsed = parse_bot_url(button_url)
        if parsed:
            bot_username, start_param = parsed
    else:
        print(f"No URL on contact button. text='{contact_button.text}' CONTACT_BOT='{CONTACT_BOT}'")

    # Avoid clicking URL buttons (prevents opening many browser tabs).
    if not bot_username:
        try:
            click_result = await message.click(text=contact_button.text)
            print(f"Click by text returned: {click_result}")
            if isinstance(click_result, str):
                parsed = parse_bot_url(click_result)
                if parsed:
                    bot_username, start_param = parsed
            elif getattr(click_result, "message", None):
                parsed = parse_bot_url(click_result.message)
                if parsed:
                    bot_username, start_param = parsed
        except Exception as exc:
            print(f"Click by text failed: {exc}")

    if not bot_username:
        return None, None

    bot_entity = await client.get_entity(bot_username)

    async with client.conversation(bot_entity, timeout=20) as conv:
        if start_param:
            await conv.send_message(f"/start {start_param}")
        else:
            await conv.send_message("/start")

        response = await conv.get_response()

    phone, owner = parse_contact_from_text(response.message)
    if not phone and not owner:
        print(f"Bot replied but no contact parsed. text='{response.message}'")
    return phone, owner


async def scrape_listings():
    if not API_ID or not API_HASH or not CHANNEL:
        raise RuntimeError("Missing TG_API_ID, TG_API_HASH, or TG_CHANNEL in .env")

    since_dt = datetime.fromisoformat(SINCE_DATE)
    if since_dt.tzinfo is None:
        since_dt = since_dt.replace(tzinfo=timezone.utc)

    client = TelegramClient("scraper", API_ID, API_HASH)
    await client.start()

    listings = []
    seen = set()
    processed = 0
    group_cache = {}
    try:
        print(f"Scanning channel since {since_dt.isoformat()}...")
        async for message in client.iter_messages(CHANNEL):
            if message.date and message.date < since_dt:
                break

            if message.grouped_id:
                group_cache.setdefault(message.grouped_id, []).append(message)

            processed += 1
            if processed % 25 == 0:
                print(f"Processed {processed} messages, scraped {len(listings)} listings...")

            text = message.text or ""
            if not text.strip():
                continue

            contact_phone, contact_owner = parse_contact_from_text(text)

            button_message = message
            if not button_message.buttons and message.grouped_id:
                for grouped_message in group_cache.get(message.grouped_id, []):
                    if grouped_message.buttons:
                        button_message = grouped_message
                        break

            if not contact_phone and button_message.buttons:
                contact_phone, contact_owner = await fetch_contact_from_button(
                    client, button_message
                )

            fields = extract_listing_fields(text)

            if fields.get("address") and (fields.get("lat") is None and fields.get("lon") is None):
                lon, lat = await geocode_address(fields.get("address"), fields.get("district"))
                fields["lon"] = lon
                fields["lat"] = lat
                print(fields.get("address"))
                print(f"{lat}, {lon}")

            payload = build_listing_payload(text, contact_phone, contact_owner, fields)
            dedupe_key = build_dedupe_key(payload)
            if dedupe_key and dedupe_key in seen:
                continue
            if dedupe_key:
                seen.add(dedupe_key)

            payload["dedupe_key"] = dedupe_key
            listings.append(payload)
    finally:
        await client.disconnect()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as handle:
        json.dump(listings, handle, ensure_ascii=False, indent=2)

    print(f"Saved {len(listings)} listings to {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        asyncio.run(scrape_listings())
    except SessionPasswordNeededError:
        print("Your account has 2FA enabled. Run again and enter the password when prompted.")
