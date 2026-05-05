from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import asyncpg
from db import get_user, create_user

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)
    
    if not user:
        create_user(telegram_id)
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
            await handle_owner_warning(query, context)
        case _:
            pass

async def handle_owner_warning(query, context: ContextTypes.DEFAULT_TYPE):
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
    
async def handle_confirm_onwer(query, context: ContextTypes.DEFAULT_TYPE):
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