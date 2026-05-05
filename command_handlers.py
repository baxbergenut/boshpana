from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import asyncpg
from db import get_user, create_user
from listing_conversation import listing_conversation_handler

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)
    
    
    if not user:
        username = update.effective_user.username
        full_name = update.effective_user.full_name
        create_user(telegram_id, username, full_name)
        await update.message.reply_text(
            "Boshpanaga xush kelibsiz! 🏠\n\nSiz kimsiz?",
           reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Ijarachi 🔍", callback_data="type_tenant")],
                [InlineKeyboardButton("Uy egasi 🏠", callback_data="type_owner")],
                [InlineKeyboardButton("Realtor 🤝", callback_data="type_realtor")]
            ])
        )
    else:
        await update.message.reply_text(f"Qaytib keldingiz! 👋")

async def process_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    match query.data:
        case "type_owner":
            print('New owner')
            await handle_confirm_owner(query, context)
        case "back_to_start":
            print('Cud not configrm, going back...')
            await handle_back_to_start(query, context)
        case "confirm_owner":
            print('Owner confirmed, asking for phone...')
            await handle_request_number(query, context)
        case "create_listing":
            print('Creating a new listing!')
            listing_conversation_handler()
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
    
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.contact.phone_number
    print(phone)
    await update.message.reply_text(
    "Sizning akkauntingiz yaratildi! ✅\nEndi siz e'lon berishingiz mumkin!",
    reply_markup=ReplyKeyboardRemove()
    )

    await update.message.reply_text(
        "Nima qilmoqchisiz?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Yangi e'lon berish 🏠", callback_data="create_listing")],
        ])
    )