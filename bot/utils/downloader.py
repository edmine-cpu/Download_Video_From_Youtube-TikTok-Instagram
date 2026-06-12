from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import yt_dlp


@dataclass(frozen=True)
class DownloadedVideo:
    path: str
    width: int | None = None
    height: int | None = None
    duration: int | None = None


@dataclass(frozen=True)
class DownloadedAudio:
    path: str
    title: str | None = None
    duration: int | None = None


def create_filename(prefix: str = "video") -> str:
    code = uuid4().hex
    filename = f"{prefix}_{code}"
    return filename


def download_video(
    url: str,
    output_path: str = "downloads",
    filename: str = "video",
) -> DownloadedVideo:
    filename = create_filename(filename)

    ydl_opts = {
        "outtmpl": f"{output_path}/{filename}.%(ext)s",
        "format": get_format(url),
        "merge_output_format": "mp4",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = get_downloaded_file_path(ydl, info, ".mp4")

    width, height = get_video_dimensions(info)

    return DownloadedVideo(
        path=file_path,
        width=width,
        height=height,
        duration=to_int(info.get("duration")),
    )


def download_audio(
    url: str,
    output_path: str = "downloads",
    filename: str = "audio",
) -> DownloadedAudio:
    filename = create_filename(filename)

    ydl_opts = {
        "outtmpl": f"{output_path}/{filename}.%(ext)s",
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = get_downloaded_file_path(ydl, info, ".mp3")

    return DownloadedAudio(
        path=file_path,
        title=info.get("title"),
        duration=to_int(info.get("duration")),
    )


def get_downloaded_file_path(ydl: yt_dlp.YoutubeDL, info: dict, extension: str | None = None) -> str:
    prepared_filename = ydl.prepare_filename(info)
    prepared_path = Path(prepared_filename)

    candidates = [
        info.get("filepath"),
        info.get("_filename"),
        prepared_filename,
    ]

    if extension and prepared_path.suffix != extension:
        candidates.append(str(prepared_path.with_suffix(extension)))

    for metadata in info.get("requested_downloads") or []:
        candidates.append(metadata.get("filepath"))
        if extension and metadata.get("filepath"):
            candidates.append(str(Path(metadata["filepath"]).with_suffix(extension)))

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)

    return prepared_filename


def get_video_dimensions(info: dict) -> tuple[int | None, int | None]:
    metadata_sources = [info]
    metadata_sources.extend(info.get("requested_downloads") or [])
    metadata_sources.extend(info.get("requested_formats") or [])

    for metadata in metadata_sources:
        width = to_int(metadata.get("width"))
        height = to_int(metadata.get("height"))
        if width and height:
            return width, height

    return None, None


def to_int(value) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_format(url: str) -> str:
    MAX_SIZE = "45M"

    if "instagram.com" in url:
        return (
            f"bestvideo[ext=mp4][vcodec^=avc1][filesize<{MAX_SIZE}]+bestaudio[ext=m4a]/"
            f"bestvideo[ext=mp4][vcodec^=avc1][filesize_approx<{MAX_SIZE}]+bestaudio[ext=m4a]/"
            f"best[ext=mp4][vcodec^=avc1][filesize<{MAX_SIZE}]/"
            f"best[ext=mp4][vcodec^=avc1][filesize_approx<{MAX_SIZE}]/"
            "best[ext=mp4]/best"
        )

    if is_youtube_url(url):
        return (
            f"bestvideo[ext=mp4][vcodec^=avc1][height<=480][filesize<{MAX_SIZE}]+bestaudio[ext=m4a]/"
            f"bestvideo[ext=mp4][vcodec^=avc1][height<=480][filesize_approx<{MAX_SIZE}]+bestaudio[ext=m4a]/"
            f"best[ext=mp4][height<=480][filesize<{MAX_SIZE}]/"
            f"best[ext=mp4][height<=480][filesize_approx<{MAX_SIZE}]/"
            f"bestvideo[ext=mp4][vcodec^=avc1][height<=360]+bestaudio[ext=m4a]/"
            f"best[ext=mp4][height<=360]/"
            "best"
        )

    return (
        f"best[filesize<{MAX_SIZE}]/"
        f"best[filesize_approx<{MAX_SIZE}]/"
        "best"
    )


def is_youtube_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com")
