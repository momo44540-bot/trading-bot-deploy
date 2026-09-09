from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _alias(name: str) -> AliasChoices:
    # بعض الطرفيات (مثل Hetzner Console) تحوّل "_" إلى "-" عند اللصق،
    # فنقبل الشكلين حتى لا يفشل تحميل الإعدادات بصمت.
    return AliasChoices(name, name.replace("_", "-"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", populate_by_name=True)

    okx_api_key: str = Field(default="", validation_alias=_alias("OKX_API_KEY"))
    okx_api_secret: str = Field(default="", validation_alias=_alias("OKX_API_SECRET"))
    okx_api_passphrase: str = Field(default="", validation_alias=_alias("OKX_API_PASSPHRASE"))
    okx_demo: bool = Field(default=False, validation_alias=_alias("OKX_DEMO"))

    app_password: str = Field(default="change-me", validation_alias=_alias("APP_PASSWORD"))
    session_secret: str = Field(default="change-this-to-a-random-long-string",
                                 validation_alias=_alias("SESSION_SECRET"))

    trading_mode: str = Field(default="paper", validation_alias=_alias("TRADING_MODE"))  # "paper" or "live"

    database_url: str = Field(default="sqlite+aiosqlite:///./trading.db",
                               validation_alias=_alias("DATABASE_URL"))

    okx_rest_base: str = "https://www.okx.com"
    okx_ws_public: str = "wss://ws.okx.com:8443/ws/v5/public"
    okx_ws_private: str = "wss://ws.okx.com:8443/ws/v5/private"


settings = Settings()
