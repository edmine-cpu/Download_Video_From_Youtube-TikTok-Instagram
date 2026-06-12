from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
	DOWNLOAD_LINKS_STATE_PATH: str = "download_links_storage/state.json"
	DOWNLOAD_LINK_USED_TTL_SECONDS: int = 10 * 60
	DOWNLOAD_LINK_CLEANUP_INTERVAL_SECONDS: int = 5 * 60

	model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = ApiSettings()
