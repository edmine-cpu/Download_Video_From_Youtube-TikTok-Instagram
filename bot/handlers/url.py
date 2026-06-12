from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from bot.service import downloader


router = Router()


@router.message()
async def download_by_url(message: Message):
	await downloader.choose_download_format(message.text, message)


@router.callback_query(F.data.startswith("download_format:"))
async def download_by_format(callback: CallbackQuery):
	await downloader.download_by_format(callback)
