from config import config
from telegram.ext import ApplicationBuilder, CommandHandler, filters, ChatMemberHandler, CallbackQueryHandler
from command_handlers import start, process_callback
from db import create_pool

async def main():
    pool = await create_pool()
    
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    app.bot_data["pool"] = pool
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(process_callback))
    
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        await asyncio.Event().wait()  # block forever

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())