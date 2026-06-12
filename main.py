from aiogram import Bot, Dispatcher
from settings import settings


dp = Dispatcher()
token = settings.BOT_TOKEN


async def main():
	bot = Bot(token=token)
	dp.start_polling(bot)