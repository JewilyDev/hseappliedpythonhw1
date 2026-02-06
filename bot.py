import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import setup_handlers
from middlewares import LoggingMiddleware

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.message.middleware(LoggingMiddleware())
setup_handlers(dp)


async def main():
    print("Бот успешно запустился")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
