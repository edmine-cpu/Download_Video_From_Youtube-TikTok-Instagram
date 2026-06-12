from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from .constants.messages import messages


router = Router()


@router.message(CommandStart())
async def start(message: Message):
	await message.answer(messages["START"])