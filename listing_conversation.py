from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, Update

CREATE_LISTING_TEXT = "Yangi e'lon berish 🏠"
from db import create_listing, insert_listing_photos


# states
# expanded to collect all fields from `listings` (except id, owner_id, status)
PHOTOS, PRICE, PRICE_NEGOTIABLE, CURRENCY, ROOMS, FLOOR, TOTAL_FLOORS, AREA, DISTRICT, ADDRESS, LOCATION, TENANT_PREFS, MAX_TENANTS, NEEDED_TENANTS, UTILS_INCLUDED, AMENITIES, DESCRIPTION, CONFIRM = range(18)

async def start_listing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["listing"] = {}
    
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "Yangi e'lon yaratamiz! 🏠\n\nAvval rasmlarni yuboring (maksimum 10).\nTugagach '✅ Tayyor' tugmasini bosing.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Tayyor", callback_data="photos_done")]
        ])
    )
    return PHOTOS

async def start_listing_from_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["listing"] = {}
    await update.message.reply_text(
        "Yangi e'lon yaratamiz! 🏠\n\nAvval rasmlarni yuboring (maksimum 10).\nTugagach '✅ Tayyor' tugmasini bosing.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Tayyor", callback_data="photos_done")]
        ])
    )
    return PHOTOS

async def handle_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photos = context.user_data["listing"].setdefault("photos", [])
    # get highest resolution file_id
    file_id = update.message.photo[-1].file_id
    photos.append(file_id)
    
    await update.message.reply_text(
        f"📸 {len(photos)} ta rasm qabul qilindi. Yana yuboring yoki '✅ Tayyor' tugmasini bosing.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Tayyor", callback_data="photos_done")]
        ])
    )
    return PHOTOS  # stay in PHOTOS state until they tap done

async def photos_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not context.user_data["listing"].get("photos"):
        await query.edit_message_text("⚠️ Kamida bitta rasm yuboring!")
        return PHOTOS
    
    await query.edit_message_text("Oylik narxni kiriting (USD) 💵\nMasalan: 400")
    return PRICE

async def handle_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Faqat raqam kiriting. Masalan: 400")
        return PRICE
    
    context.user_data["listing"]["price"] = price
    # Ask whether price is negotiable
    await update.message.reply_text(
        "Narx muzokaraga ochiqmi? (Ha/Yo'q)",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Ha", callback_data="price_neg_yes"), InlineKeyboardButton("Yo'q", callback_data="price_neg_no")]
        ])
    )
    return PRICE_NEGOTIABLE

async def handle_price_negotiable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    val = query.data
    context.user_data["listing"]["price_negotiable"] = True if val == "price_neg_yes" else False
    await query.edit_message_text("Valyutani kiriting (3 harf, masalan: USD). Bo'sh qoldirsangiz USD qabul qilinadi.")
    return CURRENCY

async def handle_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur = update.message.text.strip().upper() if update.message.text else "USD"
    context.user_data["listing"]["currency"] = cur or "USD"
    await update.message.reply_text(
        "Xonalar soni? 🚪",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("1", callback_data="rooms_1"),
                InlineKeyboardButton("2", callback_data="rooms_2"),
                InlineKeyboardButton("3", callback_data="rooms_3"),
            ],
            [
                InlineKeyboardButton("4", callback_data="rooms_4"),
                InlineKeyboardButton("5+", callback_data="rooms_5"),
            ]
        ])
    )
    return ROOMS

async def handle_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    rooms = int(query.data.split("_")[1])
    context.user_data["listing"]["rooms"] = rooms
    
    await query.edit_message_text("Nechinci qavat? Masalan: 3")
    return FLOOR

async def handle_floor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        floor = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Faqat raqam kiriting.")
        return FLOOR
    
    context.user_data["listing"]["floor"] = floor
    await update.message.reply_text("Umumiy qavatlar soni? Masalan: 9")
    return TOTAL_FLOORS

async def handle_total_floors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        total = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Faqat raqam kiriting.")
        return TOTAL_FLOORS
    
    context.user_data["listing"]["total_floors"] = total
    await update.message.reply_text("Maydon (kv.m)? Masalan: 65\nBilmasangiz 0 kiriting.")
    return AREA

async def handle_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        area = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Faqat raqam kiriting.")
        return AREA
    
    context.user_data["listing"]["area_sqm"] = area if area > 0 else None
    
    await update.message.reply_text(
        "Tuman? 🗺️",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Chilonzor", callback_data="district_Chilonzor"),
             InlineKeyboardButton("Yunusobod", callback_data="district_Yunusobod")],
            [InlineKeyboardButton("Mirzo Ulug'bek", callback_data="district_Mirzo_Ulugbek"),
             InlineKeyboardButton("Shayxontohur", callback_data="district_Shayxontohur")],
            [InlineKeyboardButton("Yakkasaroy", callback_data="district_Yakkasaroy"),
             InlineKeyboardButton("Olmazar", callback_data="district_Olmazar")],
            [InlineKeyboardButton("Uchtepa", callback_data="district_Uchtepa"),
             InlineKeyboardButton("Bektemir", callback_data="district_Bektemir")],
            [InlineKeyboardButton("Sergeli", callback_data="district_Sergeli"),
             InlineKeyboardButton("Mirobod", callback_data="district_Mirobod")],
        ])
    )
    return DISTRICT

async def handle_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    district = query.data.replace("district_", "").replace("_", " ")
    context.user_data["listing"]["district"] = district
    # after district, ask for address (optional), then location
    await query.edit_message_text(
        "Manzilni kiriting (ko'cha, uy raqami) yoki o'tkazib yuborish.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="skip_address")]
        ])
    )
    return ADDRESS

async def handle_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["listing"]["address"] = update.message.text
    await update.message.reply_text(
        "Lokatsiyangizni yuboring 📍\nYoki o'tkazib yuborish mumkin.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="skip_location")]
        ])
    )
    return LOCATION

async def skip_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Lokatsiyangizni yuboring 📍\nYoki o'tkazib yuborish mumkin.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="skip_location")]
        ])
    )
    return LOCATION

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["listing"]["lat"] = update.message.location.latitude
    context.user_data["listing"]["lon"] = update.message.location.longitude
    await update.message.reply_text("✅ Lokatsiya saqlandi!")
    # proceed to tenant preferences next
    await ask_tenant_prefs(update, context)
    return TENANT_PREFS

async def skip_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # proceed to tenant preferences even if location skipped
    await ask_tenant_prefs(update, context)
    return TENANT_PREFS


AMENITY_LIST = [
    ("has_wifi", "WiFi 📶"),
    ("has_washing_machine", "Kir yuvish mashina 🫧"),
    ("has_fridge", "Muzlatgich ❄️"),
    ("has_ac", "Konditsioner 🌬️"),
    ("has_heating", "Isitish 🔥"),
    ("has_parking", "Parking 🚗"),
    ("has_elevator", "Lift 🛗"),
    ("has_furniture", "Mebel 🪑"),
]

TENANT_PREFS_LIST = [
    ("for_boys", "Yigitlar uchun"),
    ("for_girls", "Qizlar uchun"),
    ("for_families", "Oila uchun"),
]

async def ask_amenities(update, context):
    selected = context.user_data["listing"].get("amenities", [])
    
    keyboard = []
    for key, label in AMENITY_LIST:
        check = "✅ " if key in selected else ""
        keyboard.append([InlineKeyboardButton(f"{check}{label}", callback_data=f"amenity_{key}")])
    keyboard.append([InlineKeyboardButton("✅ Tayyor", callback_data="amenities_done")])
    
    markup = InlineKeyboardMarkup(keyboard)
    text = "Qulayliklarni tanlang (bir nechtasini tanlash mumkin) 🏠"
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup)
    else:
        await update.message.reply_text(text, reply_markup=markup)


async def ask_tenant_prefs(update, context):
    selected = context.user_data["listing"].get("tenant_prefs", [])
    keyboard = []
    for key, label in TENANT_PREFS_LIST:
        check = "✅ " if key in selected else ""
        keyboard.append([InlineKeyboardButton(f"{check}{label}", callback_data=f"tenant_{key}")])
    keyboard.append([InlineKeyboardButton("✅ Tayyor", callback_data="tenant_prefs_done")])
    markup = InlineKeyboardMarkup(keyboard)
    text = "Ijaraga kimlarga mos ekanligini tanlang (bir nechtasini tanlash mumkin)"

    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup)
    else:
        await update.message.reply_text(text, reply_markup=markup)

async def handle_amenities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "amenities_done":
        await query.edit_message_text(
            "Qo'shimcha ma'lumot kiriting (ixtiyoriy) ✏️\nYoki o'tkazib yuborish mumkin.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="skip_description")]
            ])
        )
        return DESCRIPTION
    
    key = query.data.replace("amenity_", "")
    amenities = context.user_data["listing"].setdefault("amenities", [])
    
    if key in amenities:
        amenities.remove(key)  # toggle off
    else:
        amenities.append(key)  # toggle on
    
    await ask_amenities(update, context)
    return AMENITIES


async def handle_tenant_prefs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "tenant_prefs_done":
        await query.edit_message_text("Maksimal ijarachi sonini kiriting (yoki 0 agar muhim bo'lmasa)")
        return MAX_TENANTS

    key = query.data.replace("tenant_", "")
    prefs = context.user_data["listing"].setdefault("tenant_prefs", [])
    if key in prefs:
        prefs.remove(key)
    else:
        prefs.append(key)

    await ask_tenant_prefs(update, context)
    return TENANT_PREFS


async def handle_max_tenants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        v = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Faqat raqam kiriting.")
        return MAX_TENANTS
    context.user_data["listing"]["max_tenants"] = v if v > 0 else None
    await update.message.reply_text("Kerakli ijarachi (needed tenants) sonini kiriting (yoki 0)")
    return NEEDED_TENANTS


async def handle_needed_tenants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        v = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Faqat raqam kiriting.")
        return NEEDED_TENANTS
    context.user_data["listing"]["needed_tenants"] = v if v > 0 else None
    # ask if utilities included
    await update.message.reply_text(
        "Kommunal to'lovlar narxga kiritilganmi?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Ha", callback_data="utils_yes"), InlineKeyboardButton("Yo'q", callback_data="utils_no")]
        ])
    )
    return UTILS_INCLUDED


async def handle_utils_included(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["listing"]["utils_included"] = True if query.data == "utils_yes" else False
    # after utilities, go to amenities
    await ask_amenities(update, context)
    return AMENITIES

async def handle_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["listing"]["description"] = update.message.text
    await show_confirmation(update, context)
    return CONFIRM

async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_confirmation(update, context)
    return CONFIRM

async def show_confirmation(update, context):
    l = context.user_data["listing"]
    amenities = l.get("amenities", [])
    amenity_labels = [label for key, label in AMENITY_LIST if key in amenities]
    
    # build tenant prefs labels
    tenant_prefs = l.get('tenant_prefs', [])
    tenant_labels = [label for key, label in TENANT_PREFS_LIST if key in tenant_prefs]

    text = (
        f"📋 E'loningizni tekshiring:\n\n"
        f"💵 Narx: {l.get('price')} {l.get('currency', 'USD')}\n"
        f"💬 Muzokaraga ochiq: {('Ha' if l.get('price_negotiable') else 'Yo\'q')}\n"
        f"🚪 Xonalar: {l.get('rooms')}\n"
        f"🏢 Qavat: {l.get('floor')}/{l.get('total_floors')}\n"
        f"📐 Maydon: {l.get('area_sqm') or 'Noma\'lum'} kv.m\n"
        f"🗺️ Tuman: {l.get('district')}\n"
        f"🏠 Manzil: {l.get('address') or 'Yo\'q'}\n"
        f"📍 Lokatsiya: {l.get('lat') if l.get('lat') else '❌'}\n"
        f"👥 Kimlarga mos: {', '.join(tenant_labels) or 'Yo\'q'}\n"
        f"👤 Maks. ijarachi: {l.get('max_tenants') or 'Noma\'lum'}\n"
        f"🔎 Kerakli ijarachi: {l.get('needed_tenants') or 'Noma\'lum'}\n"
        f"⚙️ Kommunal kiritilgan: {('Ha' if l.get('utils_included') else 'Yo\'q')}\n"
        f"🏠 Qulayliklar: {', '.join(amenity_labels) or 'Yo\'q'}\n"
        f"📸 Rasmlar: {len(l.get('photos', []))} ta\n"
        f"📝 Tavsif: {l.get('description') or 'Yo\'q'}\n"
    )
    
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ E'lon berish", callback_data="confirm_post")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_listing")]
    ])
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup)
    else:
        await update.message.reply_text(text, reply_markup=markup)

async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_post":
        pool = context.bot_data.get("pool")
        listing = context.user_data.get("listing", {})
        result = await create_listing(pool, query.from_user.id, listing)
        photos = listing.get("photos", [])
        await insert_listing_photos(pool, result["id"], photos)
        await query.edit_message_text("🎉 E'loningiz muvaffaqiyatli joylashtirildi!")
    else:
        await query.edit_message_text("❌ E'lon bekor qilindi.")
    
    context.user_data.pop("listing", None)  # clean up
    return ConversationHandler.END

async def cancel_listing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("listing", None)
    await update.message.reply_text("❌ E'lon bekor qilindi.")
    return ConversationHandler.END

def listing_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_listing, pattern="^create_listing$"),
            MessageHandler(filters.Regex(f"^{CREATE_LISTING_TEXT}$"), start_listing_from_text),
        ],
        states={
            PHOTOS: [
                MessageHandler(filters.PHOTO, handle_photos),
                CallbackQueryHandler(photos_done, pattern="^photos_done$")
            ],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price)],
            PRICE_NEGOTIABLE: [CallbackQueryHandler(handle_price_negotiable, pattern="^price_neg_")],
            CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_currency)],
            ROOMS: [CallbackQueryHandler(handle_rooms, pattern="^rooms_")],
            FLOOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_floor)],
            TOTAL_FLOORS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_total_floors)],
            AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_area)],
            DISTRICT: [CallbackQueryHandler(handle_district, pattern="^district_")],
            ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_address),
                CallbackQueryHandler(skip_address, pattern="^skip_address$")
            ],
            LOCATION: [
                MessageHandler(filters.LOCATION, handle_location),
                CallbackQueryHandler(skip_location, pattern="^skip_location$")
            ],
            TENANT_PREFS: [CallbackQueryHandler(handle_tenant_prefs, pattern="^tenant_|^tenant_prefs_done$")],
            MAX_TENANTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_max_tenants)],
            NEEDED_TENANTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_needed_tenants)],
            UTILS_INCLUDED: [CallbackQueryHandler(handle_utils_included, pattern="^utils_")],
            AMENITIES: [CallbackQueryHandler(handle_amenities, pattern="^amenity_|^amenities_done$")],
            DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_description),
                CallbackQueryHandler(skip_description, pattern="^skip_description$")
            ],
            CONFIRM: [CallbackQueryHandler(handle_confirm, pattern="^confirm_|^cancel_listing$")]
        },
        fallbacks=[CommandHandler("cancel", cancel_listing)],
        per_message=False
    )