from config import config
from telegram.ext import ApplicationBuilder, CommandHandler, filters, MessageHandler, CallbackQueryHandler
from command_handlers import start, process_callback, handle_contact, handle_my_listings_command, MY_LISTINGS_TEXT
from listing_conversation import listing_conversation_handler
from db import create_pool

async def main():
    pool = await create_pool()
    
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    app.bot_data["pool"] = pool
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("elonlarim", handle_my_listings_command))
    app.add_handler(listing_conversation_handler())
    app.add_handler(CallbackQueryHandler(process_callback))
    app.add_handler(MessageHandler(filters.Regex(f"^{MY_LISTINGS_TEXT}$"), handle_my_listings_command))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        await asyncio.Event().wait()  # block forever

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())