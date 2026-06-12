import asyncio
from aiogram import Bot, Dispatcher
from settings import settings
from handlers import main_router


dp = Dispatcher()
token = settings.BOT_TOKEN


async def main():
	bot = Bot(token=token)
	dp.include_router(main_router)
	await dp.start_polling(bot)
	

if __name__ == "__main__":
	asyncio.run(main())