from config import config
from telegram.ext import ApplicationBuilder, CommandHandler, filters, MessageHandler, CallbackQueryHandler
from aiohttp import web
from command_handlers import (
    start,
    process_callback,
    handle_contact,
    handle_my_listings_command,
    handle_realtor_fee,
    handle_map_listings_command,
    MY_LISTINGS_TEXT,
    MAP_LISTINGS_TEXT,
)
from listing_conversation import listing_conversation_handler
from db import create_pool
from api_server import create_api_app

async def main():
    pool = await create_pool()

    api_app = create_api_app(pool)
    api_runner = web.AppRunner(api_app)
    await api_runner.setup()
    api_site = web.TCPSite(api_runner, config.API_HOST, config.API_PORT)
    await api_site.start()
    
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    app.bot_data["pool"] = pool
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("map", handle_map_listings_command))
    app.add_handler(CommandHandler("elonlarim", handle_my_listings_command))
    app.add_handler(listing_conversation_handler())
    app.add_handler(CallbackQueryHandler(process_callback))
    app.add_handler(MessageHandler(filters.Regex(f"^{MY_LISTINGS_TEXT}$"), handle_my_listings_command))
    app.add_handler(MessageHandler(filters.Regex(f"^{MAP_LISTINGS_TEXT}$"), handle_map_listings_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_realtor_fee))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        try:
            await asyncio.Event().wait()  # block forever
        finally:
            await api_runner.cleanup()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())