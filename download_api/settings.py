from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
	DOWNLOAD_LINKS_STATE_PATH: str = "download_links_storage/state.json"

	model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = ApiSettings()
