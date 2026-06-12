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


@dataclass(frozen=True)
class VideoQuality:
    height: int
    max_height: int | None = None
    filesize: int | None = None


STANDARD_VIDEO_QUALITIES = [144, 240, 360, 480, 720, 1080, 1440, 2160, 4320]


def create_filename(prefix: str = "video") -> str:
    code = uuid4().hex
    filename = f"{prefix}_{code}"
    return filename


def download_video(
    url: str,
    output_path: str = "downloads",
    filename: str = "video",
    max_height: int | None = None,
) -> DownloadedVideo:
    filename = create_filename(filename)

    ydl_opts = {
        "outtmpl": f"{output_path}/{filename}.%(ext)s",
        "format": get_format(url, max_height),
        "merge_output_format": "mp4",
        "noplaylist": True,
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


def get_video_qualities(url: str) -> list[VideoQuality]:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    formats = info.get("formats") or []
    quality_formats: dict[int, dict] = {}

    for format_info in formats:
        if not is_video_format(format_info):
            continue

        quality_height = get_standard_quality_height(format_info)
        if not quality_height:
            continue

        current_format = quality_formats.get(quality_height)
        if not current_format or video_format_score(format_info) > video_format_score(current_format):
            quality_formats[quality_height] = format_info

    if not quality_formats and (height := get_standard_quality_height(info)):
        quality_formats[height] = info

    return [
        VideoQuality(
            height=quality_height,
            max_height=to_int(format_info.get("height")) or quality_height,
            filesize=estimate_video_filesize(format_info, formats, info),
        )
        for quality_height, format_info in sorted(quality_formats.items(), reverse=True)
    ]


def download_audio(
    url: str,
    output_path: str = "downloads",
    filename: str = "audio",
) -> DownloadedAudio:
    filename = create_filename(filename)

    ydl_opts = {
        "outtmpl": f"{output_path}/{filename}.%(ext)s",
        "format": "bestaudio/best",
        "noplaylist": True,
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


def get_format(url: str, max_height: int | None = None) -> str:
    MAX_SIZE = "45M"

    if max_height and is_youtube_url(url):
        return (
            f"bestvideo[height<={max_height}][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={max_height}]+bestaudio/"
            f"best[height<={max_height}][ext=mp4]/"
            f"best[height<={max_height}]/"
            "best"
        )

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


def is_video_format(format_info: dict) -> bool:
    return format_info.get("vcodec") not in {None, "none"}


def is_audio_only_format(format_info: dict) -> bool:
    return (
        format_info.get("acodec") not in {None, "none"}
        and format_info.get("vcodec") in {None, "none"}
    )


def estimate_video_filesize(
    video_format: dict,
    formats: list[dict],
    info: dict,
) -> int | None:
    video_size = get_format_filesize(video_format, info)
    if not video_size:
        return None

    if video_format.get("acodec") not in {None, "none"}:
        return video_size

    audio_format = choose_audio_format(formats)
    audio_size = get_format_filesize(audio_format, info) if audio_format else None
    if not audio_size:
        return video_size

    return video_size + audio_size


def choose_audio_format(formats: list[dict]) -> dict | None:
    candidates = [
        format_info
        for format_info in formats
        if is_audio_only_format(format_info)
    ]
    if not candidates:
        return None

    return max(candidates, key=audio_format_score)


def get_standard_quality_height(format_info: dict) -> int | None:
    width = to_int(format_info.get("width"))
    height = to_int(format_info.get("height"))

    if width and height:
        raw_quality = min(width, height)
    else:
        raw_quality = height or width

    if not raw_quality:
        return None

    matching_qualities = [
        quality
        for quality in STANDARD_VIDEO_QUALITIES
        if quality <= raw_quality
    ]
    if matching_qualities:
        return matching_qualities[-1]

    return STANDARD_VIDEO_QUALITIES[0]


def video_format_score(format_info: dict) -> tuple[int, int, int, int, int]:
    return (
        int(format_info.get("ext") == "mp4"),
        int(str(format_info.get("vcodec") or "").startswith("avc1")),
        to_int(format_info.get("tbr")) or 0,
        get_format_filesize(format_info, {}) or 0,
        to_int(format_info.get("format_id")) or 0,
    )


def audio_format_score(format_info: dict) -> tuple[int, int, int]:
    return (
        int(format_info.get("ext") == "m4a"),
        to_int(format_info.get("abr")) or to_int(format_info.get("tbr")) or 0,
        get_format_filesize(format_info, {}) or 0,
    )


def get_format_filesize(format_info: dict | None, info: dict) -> int | None:
    if not format_info:
        return None

    filesize = to_int(format_info.get("filesize")) or to_int(format_info.get("filesize_approx"))
    if filesize:
        return filesize

    duration = to_int(format_info.get("duration")) or to_int(info.get("duration"))
    tbr = to_int(format_info.get("tbr"))
    if duration and tbr:
        return int(duration * tbr * 1000 / 8)

    return None
