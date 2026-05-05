from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, Update


# states
PHOTOS, PRICE, ROOMS, FLOOR, TOTAL_FLOORS, AREA, DISTRICT, LOCATION, DESCRIPTION, AMENITIES, CONFIRM = range(11)

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
    await ask_amenities(update, context)
    return AMENITIES

async def skip_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await ask_amenities(update, context)
    return AMENITIES


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
    
    text = (
        f"📋 E'loningizni tekshiring:\n\n"
        f"💵 Narx: {l.get('price')} USD\n"
        f"🚪 Xonalar: {l.get('rooms')}\n"
        f"🏢 Qavat: {l.get('floor')}/{l.get('total_floors')}\n"
        f"📐 Maydon: {l.get('area_sqm') or 'Noma\'lum'} kv.m\n"
        f"🗺️ Tuman: {l.get('district')}\n"
        f"📍 Lokatsiya: {l.get('lat') if l.get('lat') else '❌'}\n"
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
        # TODO: save to DB here
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
        entry_points=[CallbackQueryHandler(start_listing, pattern="^create_listing$")],
        states={
            PHOTOS: [
                MessageHandler(filters.PHOTO, handle_photos),
                CallbackQueryHandler(photos_done, pattern="^photos_done$")
            ],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price)],
            ROOMS: [CallbackQueryHandler(handle_rooms, pattern="^rooms_")],
            FLOOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_floor)],
            TOTAL_FLOORS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_total_floors)],
            AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_area)],
            DISTRICT: [CallbackQueryHandler(handle_district, pattern="^district_")],
            LOCATION: [
                MessageHandler(filters.LOCATION, handle_location),
                CallbackQueryHandler(skip_location, pattern="^skip_location$")
            ],
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