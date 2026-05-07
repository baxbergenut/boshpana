import asyncpg
from config import config

async def create_pool():
    return await asyncpg.create_pool(
        host=config.DB_HOST,
        port=config.DB_PORT,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD
    )

async def get_user(pool, user_id):
    query = (
        "SELECT id, username, phone, full_name, join_date, is_banned, type, fee "
        "FROM users WHERE id = $1"
    )
    return await pool.fetchrow(query, user_id)

async def create_user(pool, user_id, username, full_name, user_type="tenant"):
    query = (
        "INSERT INTO users (id, username, full_name, type) "
        "VALUES ($1, $2, $3, $4) "
        "ON CONFLICT (id) DO UPDATE "
        "SET username = EXCLUDED.username, full_name = EXCLUDED.full_name "
        "RETURNING id"
    )
    return await pool.fetchrow(query, user_id, username, full_name, user_type)

async def update_user_type(pool, user_id, user_type):
    query = "UPDATE users SET type = $1 WHERE id = $2"
    await pool.execute(query, user_type, user_id)

async def update_user_phone(pool, user_id, phone):
    query = "UPDATE users SET phone = $1 WHERE id = $2"
    await pool.execute(query, phone, user_id)

async def update_user_fee(pool, user_id, fee):
    query = "UPDATE users SET fee = $1 WHERE id = $2"
    await pool.execute(query, fee, user_id)

async def create_listing(pool, owner_id, listing):
    tenant_prefs = set(listing.get("tenant_prefs", []))
    amenities = set(listing.get("amenities", []))

    query = (
        "INSERT INTO listings ("
        "owner_id, lon, lat, address, district, price, currency, price_per_person, total_price, price_negotiable, "
        "rooms, floor, total_floors, area_sqm, for_boys, for_girls, "
        "for_families, shared, max_tenants, needed_tenants, utils_included, has_wifi, "
        "has_washing_machine, has_fridge, has_ac, has_heating, has_parking, "
        "has_elevator, has_furniture, description"
        ") VALUES ("
        "$1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, "
        "$15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30"
        ") RETURNING id"
    )

    price = listing.get("price")
    price_per_person = bool(listing.get("price_per_person"))
    max_tenants = listing.get("max_tenants") or 0
    if price_per_person and max_tenants > 0:
        total_price = price * max_tenants
    else:
        total_price = price

    return await pool.fetchrow(
        query,
        owner_id,
        listing.get("lon"),
        listing.get("lat"),
        listing.get("address"),
        listing.get("district"),
        price,
        (listing.get("currency") or "USD"),
        price_per_person,
        total_price,
        listing.get("price_negotiable"),
        listing.get("rooms"),
        listing.get("floor"),
        listing.get("total_floors"),
        listing.get("area_sqm"),
        "for_boys" in tenant_prefs,
        "for_girls" in tenant_prefs,
        "for_families" in tenant_prefs,
        bool(listing.get("shared")),
        listing.get("max_tenants"),
        listing.get("needed_tenants") or 0,
        listing.get("utils_included"),
        "has_wifi" in amenities,
        "has_washing_machine" in amenities,
        "has_fridge" in amenities,
        "has_ac" in amenities,
        "has_heating" in amenities,
        "has_parking" in amenities,
        "has_elevator" in amenities,
        "has_furniture" in amenities,
        listing.get("description"),
    )

async def insert_listing_photos(pool, listing_id, photos):
    rows = [(listing_id, file_id, idx) for idx, file_id in enumerate(photos)]
    if rows:
        await pool.executemany(
            "INSERT INTO listing_photos (listing_id, telegram_file_id, order_index) "
            "VALUES ($1, $2, $3)",
            rows,
        )

async def get_user_listings(pool, owner_id):
    query = (
        "SELECT id, status, price, currency, price_per_person, price_negotiable, rooms, floor, total_floors, "
        "area_sqm, district, address, lon, lat, for_boys, for_girls, for_families, "
        "max_tenants, needed_tenants, utils_included, has_wifi, has_washing_machine, "
        "has_fridge, has_ac, has_heating, has_parking, has_elevator, has_furniture, "
        "description, created_at "
        "FROM listings WHERE owner_id = $1 ORDER BY created_at DESC"
    )
    return await pool.fetch(query, owner_id)

async def get_listing_photos(pool, listing_id):
    query = (
        "SELECT telegram_file_id FROM listing_photos "
        "WHERE listing_id = $1 ORDER BY order_index ASC"
    )
    return await pool.fetch(query, listing_id)

async def get_map_listings(pool):
    query = (
        "SELECT id, lat, lon, COALESCE(total_price, price) AS price, address, district "
        "FROM listings "
        "WHERE status = 'available' AND lat IS NOT NULL AND lon IS NOT NULL"
    )
    return await pool.fetch(query)