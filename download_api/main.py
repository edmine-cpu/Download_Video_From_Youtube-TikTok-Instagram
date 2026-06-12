from contextlib import suppress
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse

from download_api.settings import settings
from download_links import consume_download_link


app = FastAPI(title="Download Video Link API")


@app.get("/health")
async def health():
	return {"status": "ok"}


@app.get("/d/{token}")
async def download_file(token: str, background_tasks: BackgroundTasks):
	download_link = consume_download_link(
		token,
		Path(settings.DOWNLOAD_LINKS_STATE_PATH),
	)

	if not download_link:
		raise HTTPException(status_code=404, detail="Link not found or expired")

	if not download_link.path.is_file():
		raise HTTPException(status_code=410, detail="File is no longer available")

	background_tasks.add_task(delete_file, download_link.path)
	return FileResponse(
		download_link.path,
		filename=download_link.filename,
		media_type="video/mp4",
		background=background_tasks,
	)


def delete_file(path: Path):
	with suppress(OSError):
		path.unlink()
