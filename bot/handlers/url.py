from aiogram import Router
from aiogram.types import Message
from .constants.messages import messages
from bot.service import downloader


router = Router()


@router.message()
async def download_by_url(message: Message):
	await downloader.download_video(message.text, message)
