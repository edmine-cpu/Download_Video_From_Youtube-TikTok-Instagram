import asyncio
import validators
from aiogram.types import Message, FSInputFile
from utils.temp_video import TempVideo
from utils.downloader import download_video as download_video_util
from handlers.constants.messages import messages


async def download_video(url: str, message: Message):
	if not validators.url(url):
		await message.answer(messages["VALIDATION_ERROR"])
		return
	

	downloaded_video = asyncio.to_thread(download_video_util, url)
	async with TempVideo(downloaded_video.path) as path:
		video = FSInputFile(path)
		await message.answer_video(
			video,
			duration=downloaded_video.duration,
			width=downloaded_video.width,
			height=downloaded_video.height,
			supports_streaming=True,
		)
		
