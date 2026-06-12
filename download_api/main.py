import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse

from download_api.settings import settings
from download_links import (
	cleanup_expired_download_links,
	get_download_link,
	mark_download_link_used,
)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
	cleanup_task = asyncio.create_task(cleanup_expired_links_periodically())

	try:
		yield
	finally:
		cleanup_task.cancel()
		with suppress(asyncio.CancelledError):
			await cleanup_task


app = FastAPI(title="Download Video Link API", lifespan=lifespan)


async def cleanup_expired_links_periodically():
	while True:
		try:
			cleanup_expired_download_links(Path(settings.DOWNLOAD_LINKS_STATE_PATH))
		except Exception:
			logger.exception("Failed to cleanup expired download links")

		await asyncio.sleep(settings.DOWNLOAD_LINK_CLEANUP_INTERVAL_SECONDS)


@app.get("/health")
async def health():
	return {"status": "ok"}


@app.head("/d/{token}")
async def check_download_file(token: str):
	download_link = get_download_link(
		token,
		Path(settings.DOWNLOAD_LINKS_STATE_PATH),
	)

	if not download_link:
		raise_download_link_not_found()

	if not download_link.path.is_file():
		raise HTTPException(status_code=410, detail="File is no longer available")

	return Response(
		media_type="video/mp4",
		headers=create_download_headers(download_link.path, download_link.filename),
	)


@app.get("/d/{token}")
async def download_file(token: str):
	download_link = mark_download_link_used(
		token,
		Path(settings.DOWNLOAD_LINKS_STATE_PATH),
		settings.DOWNLOAD_LINK_USED_TTL_SECONDS,
	)

	if not download_link:
		raise_download_link_not_found()

	if not download_link.path.is_file():
		raise HTTPException(status_code=410, detail="File is no longer available")

	return FileResponse(
		download_link.path,
		filename=download_link.filename,
		media_type="video/mp4",
	)


def raise_download_link_not_found():
	raise HTTPException(status_code=404, detail="Link not found or expired")


def create_download_headers(path: Path, filename: str) -> dict[str, str]:
	return {
		"Accept-Ranges": "bytes",
		"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
		"Content-Length": str(path.stat().st_size),
	}
