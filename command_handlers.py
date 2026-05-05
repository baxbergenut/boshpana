from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from db import get_user, create_user, update_user_type, update_user_phone, get_user_listings
from listing_conversation import listing_conversation_handler, CREATE_LISTING_TEXT

MY_LISTINGS_TEXT = "Mening e'lonlarim 📋"
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
        await update.message.reply_text(
            "Qaytib keldingiz! 👋\n\nNima qilmoqchisiz?",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton(CREATE_LISTING_TEXT)], [KeyboardButton(MY_LISTINGS_TEXT)]],
                resize_keyboard=True,
            ),
        )

async def process_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    match query.data:
        case "type_tenant":
            await handle_set_type(query, context, "tenant")
        case "type_realtor":
            await handle_set_type(query, context, "realtor")
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
            print('Creating a new listing!')
            listing_conversation_handler()
        case "my_listings":
            await handle_my_listings(query, context)
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

async def handle_set_type(query, context: ContextTypes.DEFAULT_TYPE, user_type: str):
    pool = context.bot_data.get("pool")
    await update_user_type(pool, query.from_user.id, user_type)
    if user_type in ("tenant", "realtor"):
        await query.edit_message_text(
            "Tanlovingiz saqlandi. Rahmat!"
        )
    
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.contact.phone_number
    pool = context.bot_data.get("pool")
    await update_user_phone(pool, update.effective_user.id, phone)
    await update.message.reply_text(
    "Sizning akkauntingiz yaratildi! ✅\nEndi siz e'lon berishingiz mumkin!",
    reply_markup=ReplyKeyboardMarkup(
        [[KeyboardButton(CREATE_LISTING_TEXT)], [KeyboardButton(MY_LISTINGS_TEXT)]],
        resize_keyboard=True,
    )
    )

    await update.message.reply_text("Nima qilmoqchisiz?")

def build_listings_text(listings):
    lines = ["Sizning e'lonlaringiz:"]
    for row in listings:
        status_label = STATUS_LABELS_UZ.get(row["status"], row["status"])
        lines.append(
            f"#{row['id']} | {row['price']} {row['currency']} | {row['rooms']} xonali | "
            f"{row['district']} | {status_label}"
        )
    return "\n".join(lines)

async def handle_my_listings(query, context: ContextTypes.DEFAULT_TYPE):
    pool = context.bot_data.get("pool")
    listings = await get_user_listings(pool, query.from_user.id)
    if not listings:
        await query.edit_message_text("Sizda hali e'lonlar yo'q.")
        return

    await query.edit_message_text(build_listings_text(listings))

async def handle_my_listings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pool = context.bot_data.get("pool")
    listings = await get_user_listings(pool, update.effective_user.id)
    if not listings:
        await update.message.reply_text("Sizda hali e'lonlar yo'q.")
        return

    await update.message.reply_text(build_listings_text(listings))