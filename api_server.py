from decimal import Decimal
from aiohttp import web
from config import config
from db import get_map_listings


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
async def auth_middleware(request, handler):
    if request.method == "OPTIONS":
        return await handler(request)

    if request.path == "/api/listings":
        api_key = config.API_KEY
        if not api_key:
            return web.json_response({"error": "API key not configured"}, status=500)

        provided = request.headers.get("x-api-key")
        if provided != api_key:
            return web.json_response({"error": "Unauthorized"}, status=401)

    return await handler(request)


@web.middleware
async def cors_middleware(request, handler):
    response = await handler(request)
    allowed = _get_allowed_origins()
    origin = request.headers.get("Origin")

    if allowed == "*":
        response.headers["Access-Control-Allow-Origin"] = "*"
    elif origin in allowed:
        response.headers["Access-Control-Allow-Origin"] = origin

    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-API-Key"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response


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


def create_api_app(pool):
    app = web.Application(middlewares=[auth_middleware, cors_middleware])
    app["pool"] = pool
    app.router.add_route("OPTIONS", "/api/listings", handle_options)
    app.router.add_get("/api/listings", handle_listings)
    return app
