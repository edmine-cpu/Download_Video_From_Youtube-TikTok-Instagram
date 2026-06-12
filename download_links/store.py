from __future__ import annotations

import json
import secrets
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fcntl


@dataclass(frozen=True)
class DownloadLink:
	path: Path
	filename: str
	expires_at: float


def create_download_link(
	file_path: Path,
	state_path: Path,
	ttl_seconds: int,
	filename: str | None = None,
) -> str:
	file_path = file_path.resolve()
	token = secrets.token_urlsafe(32)
	expires_at = time.time() + ttl_seconds

	with _locked_state(state_path) as state:
		_cleanup_expired_links(state)
		state[token] = {
			"path": str(file_path),
			"filename": filename or file_path.name,
			"expires_at": expires_at,
		}

	return token


def consume_download_link(token: str, state_path: Path) -> DownloadLink | None:
	with _locked_state(state_path) as state:
		_cleanup_expired_links(state)
		raw_link = state.pop(token, None)

	if not raw_link:
		return None

	expires_at = _to_float(raw_link.get("expires_at"))
	if expires_at <= time.time():
		_delete_file(raw_link.get("path"))
		return None

	path = Path(str(raw_link.get("path", ""))).resolve()
	filename = str(raw_link.get("filename") or path.name)
	return DownloadLink(path=path, filename=filename, expires_at=expires_at)


class _locked_state:
	def __init__(self, state_path: Path):
		self.state_path = state_path
		self.file = None
		self.state: dict[str, dict[str, Any]] = {}

	def __enter__(self) -> dict[str, dict[str, Any]]:
		self.state_path.parent.mkdir(parents=True, exist_ok=True)
		self.file = self.state_path.open("a+", encoding="utf-8")
		fcntl.flock(self.file.fileno(), fcntl.LOCK_EX)
		self.file.seek(0)
		raw_state = self.file.read()
		self.state = _decode_state(raw_state)
		return self.state

	def __exit__(self, exc_type, exc, tb):
		if not self.file:
			return

		if exc_type is None:
			self.file.seek(0)
			json.dump(self.state, self.file, ensure_ascii=False)
			self.file.truncate()
			self.file.flush()

		fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
		self.file.close()


def _decode_state(raw_state: str) -> dict[str, dict[str, Any]]:
	if not raw_state.strip():
		return {}

	with suppress(json.JSONDecodeError):
		state = json.loads(raw_state)
		if isinstance(state, dict):
			return {
				str(token): link
				for token, link in state.items()
				if isinstance(link, dict)
			}

	return {}


def _cleanup_expired_links(state: dict[str, dict[str, Any]]):
	now = time.time()
	expired_tokens = [
		token
		for token, link in state.items()
		if _to_float(link.get("expires_at")) <= now
	]

	for token in expired_tokens:
		link = state.pop(token, None)
		if link:
			_delete_file(link.get("path"))


def _delete_file(path: object):
	if not path:
		return

	with suppress(OSError):
		Path(str(path)).unlink()


def _to_float(value: object) -> float:
	try:
		return float(value)
	except (TypeError, ValueError):
		return 0
