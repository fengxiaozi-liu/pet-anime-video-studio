from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # Jimeng provider config
    JIMENG_APP_KEY: Optional[str] = None
    JIMENG_APP_SECRET: Optional[str] = None
    JIMENG_REQ_KEY: str = "jimeng_ti2v_v30_pro"
    DATABASE_PATH: Path = Path(".data/tasks.db")

    # App Settings
    DEBUG: bool = False
    UPLOAD_DIR: Path = Path("uploads")
    OUTPUT_DIR: Path = Path("outputs")
    DATA_DIR: Path = Path(".data")

    # Configuration for .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def __init__(self, **values):
        super().__init__(**values)
        # Ensure directories exist
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
