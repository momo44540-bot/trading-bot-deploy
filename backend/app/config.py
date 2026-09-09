from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    okx_api_key: str = ""
    okx_api_secret: str = ""
    okx_api_passphrase: str = ""
    okx_demo: bool = False

    app_password: str = "change-me"
    session_secret: str = "change-this-to-a-random-long-string"

    trading_mode: str = "paper"  # "paper" or "live"

    database_url: str = "sqlite+aiosqlite:///./trading.db"

    okx_rest_base: str = "https://www.okx.com"
    okx_ws_public: str = "wss://ws.okx.com:8443/ws/v5/public"
    okx_ws_private: str = "wss://ws.okx.com:8443/ws/v5/private"


settings = Settings()
