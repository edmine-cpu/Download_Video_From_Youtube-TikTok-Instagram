import yt_dlp
from pathlib import Path
from uuid import uuid4


def create_filename(prefix: str = "video") -> str:
	code = uuid4().hex
	filename = f"{prefix}_{code}"
	return filename
	

def download_video(url: str, output_path: str = "downloads", filename: str = "video"):
	filename = create_filename()

	MAX_SIZE = "45M"

	ydl_opts = {
		"outtmpl": f"{output_path}/{filename}.%(ext)s",
		"format": (
			f"bestvideo[filesize<{MAX_SIZE}]+bestaudio[filesize<{MAX_SIZE}]/"
			f"bestvideo[filesize_approx<{MAX_SIZE}]+bestaudio[filesize_approx<{MAX_SIZE}]/"
			f"best[filesize<{MAX_SIZE}]/"
			f"best[filesize_approx<{MAX_SIZE}]/"
			"worst"
		),
		"merge_output_format": "mp4",
	}

	with yt_dlp.YoutubeDL(ydl_opts) as ydl:
		info = ydl.extract_info(url, download=True)
		file_path = ydl.prepare_filename(info)


	return file_path



