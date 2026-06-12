import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
from time import monotonic
from uuid import uuid4

import validators
from aiogram.types import (
	CallbackQuery,
	FSInputFile,
	InlineKeyboardButton,
	InlineKeyboardMarkup,
	Message,
)
from bot.utils.temp_video import TempVideo
from bot.utils.downloader import (
	download_audio as download_audio_util,
	download_video as download_video_util,
	is_youtube_url,
)
from bot.handlers.constants.messages import messages


DOWNLOAD_FORMAT_PREFIX = "download_format:"
DOWNLOAD_URL_TTL_SECONDS = 15 * 60
TELEGRAM_AUDIO_MAX_BYTES = 50 * 1024 * 1024
DOWNLOAD_WORKERS = 2


@dataclass(frozen=True)
class PendingDownload:
	url: str
	expires_at: float


_download_urls: dict[str, PendingDownload] = {}
_download_cleanup_tasks: set[asyncio.Task[None]] = set()
_download_executor = ThreadPoolExecutor(
	max_workers=DOWNLOAD_WORKERS,
	thread_name_prefix="download",
)


async def choose_download_format(url: str | None, message: Message):
	url = (url or "").strip()

	if not validators.url(url):
		await message.answer(messages["VALIDATION_ERROR"])
		return

	request_id = uuid4().hex
	expires_at = monotonic() + DOWNLOAD_URL_TTL_SECONDS
	_download_urls[request_id] = PendingDownload(url=url, expires_at=expires_at)
	schedule_download_url_cleanup(request_id, expires_at)

	await message.answer(
		messages["CHOOSE_FORMAT"],
		reply_markup=create_format_keyboard(request_id, url),
	)


async def download_by_format(callback: CallbackQuery):
	await callback.answer()

	message = callback.message
	if not isinstance(message, Message):
		return

	format_type, request_id = parse_callback_data(callback.data)
	if format_type not in {"mp3", "mp4"} or not request_id:
		await message.answer(messages["DOWNLOAD_REQUEST_EXPIRED"])
		return

	url = get_active_download_url(request_id)

	if not url:
		await message.answer(messages["DOWNLOAD_REQUEST_EXPIRED"])
		return

	if format_type == "mp3" and not is_youtube_url(url):
		await message.answer(messages["YOUTUBE_MP3_ONLY"])
		return

	_download_urls.pop(request_id, None)
	await message.edit_text(messages["DOWNLOAD_STARTED"])

	if format_type == "mp3":
		await download_audio(url, message)
		return

	await download_video(url, message)


def create_format_keyboard(request_id: str, url: str) -> InlineKeyboardMarkup:
	buttons = []

	if is_youtube_url(url):
		buttons.append(
			InlineKeyboardButton(
				text="MP3",
				callback_data=f"{DOWNLOAD_FORMAT_PREFIX}mp3:{request_id}",
			)
		)

	buttons.append(
		InlineKeyboardButton(
			text="MP4",
			callback_data=f"{DOWNLOAD_FORMAT_PREFIX}mp4:{request_id}",
		)
	)

	return InlineKeyboardMarkup(
		inline_keyboard=[
			buttons
		]
	)


def parse_callback_data(data: str | None) -> tuple[str, str]:
	if not data:
		return "", ""

	data = data.removeprefix(DOWNLOAD_FORMAT_PREFIX)
	callback_parts = data.split(":", maxsplit=1)
	if len(callback_parts) != 2:
		return "", ""

	format_type, request_id = callback_parts
	return format_type, request_id


def get_active_download_url(request_id: str) -> str | None:
	pending_download = _download_urls.get(request_id)
	if not pending_download:
		return None

	if pending_download.expires_at <= monotonic():
		_download_urls.pop(request_id, None)
		return None

	return pending_download.url


def schedule_download_url_cleanup(request_id: str, expires_at: float):
	cleanup_task = asyncio.create_task(remove_expired_download_url(request_id, expires_at))
	_download_cleanup_tasks.add(cleanup_task)
	cleanup_task.add_done_callback(_download_cleanup_tasks.discard)


async def remove_expired_download_url(request_id: str, expires_at: float):
	await asyncio.sleep(max(0, expires_at - monotonic()))

	pending_download = _download_urls.get(request_id)
	if pending_download and pending_download.expires_at <= monotonic():
		_download_urls.pop(request_id, None)


async def run_download_in_thread(download_func, url: str):
	loop = asyncio.get_running_loop()
	return await loop.run_in_executor(
		_download_executor,
		partial(download_func, url),
	)


async def download_video(url: str, message: Message):
	if not validators.url(url):
		await message.answer(messages["VALIDATION_ERROR"])
		return

	downloaded_video = await run_download_in_thread(download_video_util, url)
	async with TempVideo(downloaded_video.path) as path:
		video = FSInputFile(path)
		await message.answer_video(
			video,
			duration=downloaded_video.duration,
			width=downloaded_video.width,
			height=downloaded_video.height,
			supports_streaming=True,
		)


async def download_audio(url: str, message: Message):
	if not validators.url(url):
		await message.answer(messages["VALIDATION_ERROR"])
		return

	if not is_youtube_url(url):
		await message.answer(messages["YOUTUBE_MP3_ONLY"])
		return

	downloaded_audio = await run_download_in_thread(download_audio_util, url)
	async with TempVideo(downloaded_audio.path) as path:
		if path.stat().st_size > TELEGRAM_AUDIO_MAX_BYTES:
			await message.answer(messages["AUDIO_TOO_LARGE"])
			return

		audio = FSInputFile(path)
		await message.answer_audio(
			audio,
			duration=downloaded_audio.duration,
			title=downloaded_audio.title,
		)
