import asyncio
from decimal import Decimal

import aiohttp
from aiohttp import web

from config import config
from db import get_listing_photos, get_map_listings, get_public_listing_by_id


def _to_float(value):
    if isinstance(value, Decimal):
        return float(value)
    return value


def _get_allowed_origins():
    raw = (config.API_ALLOWED_ORIGINS or "*").strip()
    if raw == "*":
        return "*"
    return [item.strip() for item in raw.split(",") if item.strip()]


@web.middleware
async def cors_middleware(request, handler):
    response = await handler(request)
    allowed = _get_allowed_origins()
    origin = request.headers.get("Origin")

    if allowed == "*":
        response.headers["Access-Control-Allow-Origin"] = "*"
    elif origin in allowed:
        response.headers["Access-Control-Allow-Origin"] = origin

    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, X-API-Key, ngrok-skip-browser-warning"
    )
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response


@web.middleware
async def auth_middleware(request, handler):
    if request.method == "OPTIONS":
        return await handler(request)

    if request.path.startswith("/api/listings"):
        api_key = config.API_KEY
        if not api_key:
            return web.json_response({"error": "API key not configured"}, status=500)

        provided = request.headers.get("x-api-key")
        if provided != api_key:
            return web.json_response({"error": "Unauthorized"}, status=401)

    return await handler(request)


async def handle_options(request):
    return web.Response(status=204)


async def handle_listings(request):
    pool = request.app["pool"]
    rows = await get_map_listings(pool)
    data = []
    for row in rows:
        data.append(
            {
                "id": str(row["id"]),
                "lat": _to_float(row["lat"]),
                "lon": _to_float(row["lon"]),
                "price": row["price"],
                "address": row["address"],
                "district": row["district"],
            }
        )
    return web.json_response(data)


def _serialize_listing(row):
    tenant_prefs = []
    if row["for_boys"]:
        tenant_prefs.append("for_boys")
    if row["for_girls"]:
        tenant_prefs.append("for_girls")
    if row["for_families"]:
        tenant_prefs.append("for_families")

    amenities = []
    for key in (
        "has_wifi",
        "has_washing_machine",
        "has_fridge",
        "has_ac",
        "has_heating",
        "has_parking",
        "has_elevator",
        "has_furniture",
    ):
        if row[key]:
            amenities.append(key)

    created_at = row["created_at"]
    return {
        "id": str(row["id"]),
        "status": row["status"],
        "price": row["price"],
        "currency": row["currency"],
        "price_per_person": row["price_per_person"],
        "price_negotiable": row["price_negotiable"],
        "rooms": row["rooms"],
        "floor": row["floor"],
        "total_floors": row["total_floors"],
        "area_sqm": _to_float(row["area_sqm"]),
        "district": row["district"],
        "address": row["address"],
        "lat": _to_float(row["lat"]),
        "lon": _to_float(row["lon"]),
        "shared": row["shared"],
        "max_tenants": row["max_tenants"],
        "needed_tenants": row["needed_tenants"],
        "utils_included": row["utils_included"],
        "tenant_prefs": tenant_prefs,
        "amenities": amenities,
        "description": row["description"],
        "owner_username": row["username"],
        "owner_phone": row["phone"],
        "created_at": created_at.isoformat() if created_at else None,
    }


async def _fetch_telegram_file_url(session, token, file_id):
    url = f"https://api.telegram.org/bot{token}/getFile"
    async with session.get(url, params={"file_id": file_id}) as response:
        if response.status != 200:
            return None
        payload = await response.json()
        file_path = payload.get("result", {}).get("file_path")
        if not file_path:
            return None
        return f"https://api.telegram.org/file/bot{token}/{file_path}"


async def _build_photo_payload(file_ids):
    if not file_ids:
        return []

    token = config.TELEGRAM_TOKEN
    if not token:
        return [{"id": file_id, "url": None} for file_id in file_ids]

    async with aiohttp.ClientSession() as session:
        tasks = [
            _fetch_telegram_file_url(session, token, file_id)
            for file_id in file_ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    payload = []
    for file_id, result in zip(file_ids, results):
        url = result if isinstance(result, str) else None
        payload.append({"id": file_id, "url": url})

    return payload


async def handle_listing_detail(request):
    listing_id = request.match_info.get("listing_id")
    pool = request.app["pool"]
    row = await get_public_listing_by_id(pool, listing_id)
    if not row:
        return web.json_response({"error": "Listing not found"}, status=404)

    photo_rows = await get_listing_photos(pool, listing_id)
    file_ids = [row["telegram_file_id"] for row in photo_rows]
    photos = await _build_photo_payload(file_ids)

    data = _serialize_listing(row)
    data["photos"] = photos
    return web.json_response(data)


def create_api_app(pool):
    app = web.Application(middlewares=[cors_middleware, auth_middleware])
    app["pool"] = pool
    app.router.add_route("OPTIONS", "/api/listings", handle_options)
    app.router.add_route("OPTIONS", "/api/listings/{listing_id}", handle_options)
    app.router.add_get("/api/listings", handle_listings)
    app.router.add_get("/api/listings/{listing_id}", handle_listing_detail)
    return app
