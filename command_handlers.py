from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, WebAppInfo
from telegram.ext import ContextTypes
from db import get_user, create_user, update_user_type, update_user_phone, update_user_fee, get_user_listings, get_listing_photos, update_listing_status, delete_listing, get_listing_by_id
from config import config
from listing_conversation import listing_conversation_handler, CREATE_LISTING_TEXT, AMENITY_LIST, TENANT_PREFS_LIST

MY_LISTINGS_TEXT = "Mening e'lonlarim 📋"
MAP_LISTINGS_TEXT = "Xaritada e'lonlar 🗺️"
STATUS_LABELS_UZ = {
    "available": "Bo'sh",
    "taken": "Band",
    "disabled": "O'chirilgan",
    "pending": "Kutilmoqda",
    "rejected": "Rad etilgan",
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    pool = context.bot_data.get("pool")
    user = await get_user(pool, telegram_id)
    
    
    if not user:
        username = update.effective_user.username
        full_name = update.effective_user.full_name
        await create_user(pool, telegram_id, username, full_name)
        await update.message.reply_text(
            "Boshpanaga xush kelibsiz! 🏠\n\nSiz kimsiz?",
           reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Ijarachi 🔍", callback_data="type_tenant")],
                [InlineKeyboardButton("Uy egasi 🏠", callback_data="type_owner")],
                [InlineKeyboardButton("Realtor 🤝", callback_data="type_realtor")]
            ])
        )
    else:
        user_type = user["type"]
        if user_type == "tenant":
            buttons = [[KeyboardButton(MAP_LISTINGS_TEXT)]]
        else:
            buttons = [[KeyboardButton(CREATE_LISTING_TEXT)], [KeyboardButton(MY_LISTINGS_TEXT)]]
        await update.message.reply_text(
            "Qaytib keldingiz! 👋\n\nNima qilmoqchisiz?",
            reply_markup=ReplyKeyboardMarkup(
                buttons,
                resize_keyboard=True,
            ),
        )

async def process_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("listing_status:"):
        _, listing_id, next_status = query.data.split(":", 2)
        pool = context.bot_data.get("pool")
        result = await update_listing_status(pool, listing_id, query.from_user.id, next_status)
        if not result.endswith("1"):
            await query.message.reply_text("Holat yangilanmadi. Qayta urinib ko'ring.")
            return

        row = await get_listing_by_id(pool, listing_id, query.from_user.id)
        if not row:
            await query.message.reply_text("E'lon topilmadi.")
            return

        caption = build_listing_caption(row)
        actions = build_listing_actions(row)
        if query.message.photo:
            await query.edit_message_caption(caption=caption, reply_markup=actions)
        else:
            await query.edit_message_text(text=caption, reply_markup=actions)
        return

    if query.data.startswith("listing_delete:"):
        _, listing_id = query.data.split(":", 1)
        pool = context.bot_data.get("pool")
        result = await delete_listing(pool, listing_id, query.from_user.id)
        if result.endswith("1"):
            await query.message.delete()
            await query.message.reply_text("E'lon o'chirildi.")
        else:
            await query.message.reply_text("E'lon o'chirilmadi. Qayta urinib ko'ring.")
        return

    match query.data:
        case "type_tenant":
            await handle_set_type(query, context, "tenant")
        case "type_realtor":
            await handle_realtor_start(query, context)
        case "type_owner":
            print('New owner')
            await handle_confirm_owner(query, context)
        case "back_to_start":
            print('Cud not configrm, going back...')
            await handle_back_to_start(query, context)
        case "confirm_owner":
            print('Owner confirmed, asking for phone...')
            await handle_set_type(query, context, "owner")
            await handle_request_number(query, context)
        case "create_listing":
            pool = context.bot_data.get("pool")
            user = await get_user(pool, query.from_user.id)
            if user and user.get("type") == "tenant":
                await query.message.reply_text(
                    "Ijarachilar uchun e'lon berish mavjud emas."
                )
                return
            print("Creating a new listing!")
            listing_conversation_handler()
        case "my_listings":
            await handle_my_listings(update, context)
        case _:
            pass
    
async def handle_confirm_owner(query, context: ContextTypes.DEFAULT_TYPE):
    await query.edit_message_text(
            "⚠️ Diqqat!\n\n"
            "Iltimos, halol javob bering.\n"
            "Agar uy egasi sifatida ro'yxatdan o'tsangiz, "
            "lekin rieltor bo'lib chiqsangiz — "
            "barcha e'lonlaringiz o'chiriladi va akkauntingiz bloklanadi.\n\n"
            "Davom etasizmi?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Ha, men haqiqiy uy egasiman ✅", callback_data="confirm_owner")],
                [InlineKeyboardButton("Orqaga 🔙", callback_data="back_to_start")]
            ])
        )
    
async def handle_back_to_start(query, context: ContextTypes.DEFAULT_TYPE):
    await query.edit_message_text(
        "Boshpanaga xush kelibsiz! 🏠\n\nSiz kimsiz?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Ijarachi 🔍", callback_data="type_tenant")],
            [InlineKeyboardButton("Uy egasi 🏠", callback_data="type_owner")],
            [InlineKeyboardButton("Realtor 🤝", callback_data="type_realtor")]
        ])
    )

async def handle_request_number(query, context: ContextTypes.DEFAULT_TYPE):
    await query.message.delete()
    await query.message.reply_text(
    "Telefon raqamingizni yuboring 📱",
    reply_markup=ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
)

async def handle_request_number_from_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Telefon raqamingizni yuboring 📱",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Raqamni yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )

async def handle_set_type(query, context: ContextTypes.DEFAULT_TYPE, user_type: str):
    pool = context.bot_data.get("pool")
    await update_user_type(pool, query.from_user.id, user_type)
    if user_type in ("tenant",):
        await query.edit_message_text("Tanlovingiz saqlandi. Rahmat!")
        await query.message.reply_text(
            "Nima qilmoqchisiz?",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton(MAP_LISTINGS_TEXT)]],
                resize_keyboard=True,
            ),
        )

async def handle_realtor_start(query, context: ContextTypes.DEFAULT_TYPE):
    pool = context.bot_data.get("pool")
    await update_user_type(pool, query.from_user.id, "realtor")
    context.user_data["awaiting_realtor_fee"] = True
    await query.edit_message_text(
        "Rieltorlik foizini kiriting (0-100). Masalan: 10 yoki 15.5"
    )

async def handle_realtor_fee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_realtor_fee"):
        return

    raw_fee = (update.message.text or "").strip().replace(",", ".")
    try:
        fee = float(raw_fee)
    except ValueError:
        await update.message.reply_text("⚠️ Faqat raqam kiriting. Masalan: 10 yoki 15.5")
        return
    if fee < 0 or fee > 100:
        await update.message.reply_text("⚠️ Foiz 0 va 100 orasida bo'lishi kerak.")
        return

    pool = context.bot_data.get("pool")
    await update_user_fee(pool, update.effective_user.id, fee)
    context.user_data.pop("awaiting_realtor_fee", None)
    context.user_data["awaiting_realtor_phone"] = True

    await update.message.reply_text("Rahmat! Endi telefon raqamingizni yuboring. ✅")
    await handle_request_number_from_text(update, context)
    
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.contact.phone_number
    pool = context.bot_data.get("pool")
    await update_user_phone(pool, update.effective_user.id, phone)
    awaiting_realtor_phone = context.user_data.pop("awaiting_realtor_phone", None)
    if awaiting_realtor_phone:
        await update.message.reply_text(
            "Raqamingiz saqlandi! ✅\nEndi yangi e'lon berishni xohlaysizmi?",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton(CREATE_LISTING_TEXT)], [KeyboardButton(MY_LISTINGS_TEXT)]],
                resize_keyboard=True,
            ),
        )
        return
    await update.message.reply_text(
    "Sizning akkauntingiz yaratildi! ✅\nEndi siz e'lon berishingiz mumkin!",
    reply_markup=ReplyKeyboardMarkup(
        [[KeyboardButton(CREATE_LISTING_TEXT)], [KeyboardButton(MY_LISTINGS_TEXT)]],
        resize_keyboard=True,
    )
    )

    await update.message.reply_text("Nima qilmoqchisiz?")

async def handle_map_listings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not config.WEB_APP_URL:
        await update.message.reply_text("Map sozlanmagan. Admin bilan bog'laning.")
        return

    await update.message.reply_text(
        "Xaritani ochish uchun tugmani bosing:",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Xaritani ochish", web_app=WebAppInfo(url=config.WEB_APP_URL))]]
        ),
    )

def build_listing_caption(row):
    status_label = STATUS_LABELS_UZ.get(row["status"], row["status"])
    tenant_labels = [label for key, label in TENANT_PREFS_LIST if row[key]]
    amenity_labels = [label for key, label in AMENITY_LIST if row[key]]
    area = f"{row['area_sqm']} kv.m" if row["area_sqm"] else "Noma'lum"
    address = row["address"] or "Yo'q"
    location = "Bor" if row["lat"] and row["lon"] else "Yo'q"

    needed_label = row["needed_tenants"] if row["needed_tenants"] else "Yo'q"
    currency = row.get("currency") or "USD"
    price_suffix = " odam boshiga" if row.get("price_per_person") else ""

    return (
        f"📋 E'lon ma'lumoti:\n"
        f"📌 Holat: {status_label}\n"
        f"💵 Narx: {row['price']} {currency}{price_suffix}\n"
        f"💬 Muzokaraga ochiq: {('Ha' if row['price_negotiable'] else 'Yo\'q')}\n"
        f"🚪 Xonalar: {row['rooms']}\n"
        f"🏢 Qavat: {row['floor']}/{row['total_floors']}\n"
        f"📐 Maydon: {area}\n"
        f"🗺️ Tuman: {row['district']}\n"
        f"🏠 Manzil: {address}\n"
        f"📍 Lokatsiya: {location}\n"
        f"👥 Kimlarga mos: {', '.join(tenant_labels) or 'Yo\'q'}\n"
        f"👤 Maks. ijarachi: {row['max_tenants'] or 'Noma\'lum'}\n"
        f"🔎 Kerakli ijarachi: {needed_label}\n"
        f"⚙️ Kommunal kiritilgan: {('Ha' if row['utils_included'] else 'Yo\'q')}\n"
        f"🏠 Qulayliklar: {', '.join(amenity_labels) or 'Yo\'q'}\n"
        f"📝 Tavsif: {row['description'] or 'Yo\'q'}"
    )

def build_listing_actions(row):
    next_status = "taken" if row["status"] == "available" else "available"
    status_label = "Band qilish" if next_status == "taken" else "Bo'shatish"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(status_label, callback_data=f"listing_status:{row['id']}:{next_status}")],
            [InlineKeyboardButton("E'lonni o'chirish", callback_data=f"listing_delete:{row['id']}")],
        ]
    )

async def send_user_listings(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    pool = context.bot_data.get("pool")
    listings = await get_user_listings(pool, user_id)
    if not listings:
        if update.callback_query:
            await update.callback_query.edit_message_text("Sizda hali e'lonlar yo'q.")
        else:
            await update.message.reply_text("Sizda hali e'lonlar yo'q.")
        return

    if update.callback_query:
        await update.callback_query.edit_message_text("Sizning e'lonlaringiz:")
    else:
        await update.message.reply_text("Sizning e'lonlaringiz:")

    chat_id = update.effective_chat.id
    for row in listings:
        caption = build_listing_caption(row)
        actions = build_listing_actions(row)
        photos = await get_listing_photos(pool, row["id"])
        if photos:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photos[0]["telegram_file_id"],
                caption=caption,
                reply_markup=actions,
            )
        else:
            await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=actions)

async def handle_my_listings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pool = context.bot_data.get("pool")
    user = await get_user(pool, update.effective_user.id)
    if user and user.get("type") == "tenant":
        if update.callback_query:
            await update.callback_query.message.reply_text(
                "Ijarachilar uchun e'lonlar bo'limi mavjud emas."
            )
        else:
            await update.message.reply_text(
                "Ijarachilar uchun e'lonlar bo'limi mavjud emas."
            )
        return
    await send_user_listings(update, context, update.effective_user.id)

async def handle_my_listings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pool = context.bot_data.get("pool")
    user = await get_user(pool, update.effective_user.id)
    if user and user.get("type") == "tenant":
        await update.message.reply_text(
            "Ijarachilar uchun e'lonlar bo'limi mavjud emas."
        )
        return
    await send_user_listings(update, context, update.effective_user.id)