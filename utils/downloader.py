import yt_dlp
from pathlib import Path
from uuid import uuid4


def create_filename(prefix: str = "video") -> str:
	code = uuid4().hex
	filename = f"{prefix}_{code}"
	return filename
	

def download_video(url: str, output_path: str = "downloads", filename: str = "video"):
	filename = create_filename()


	ydl_opts = {
		"outtmpl": f"{output_path}/{filename}.%(ext)s",
	}


	with yt_dlp.YoutubeDL(ydl_opts) as ydl:
		info = ydl.extract_info(url, download=True)
		file_path = ydl.prepare_filename(info)


	return file_path



