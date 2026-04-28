from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    gmail_email: str
    gmail_app_password: str
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    target_subject: str = "[업무 협조]"
    
    attachment_dir: Path = Path("data/attachments")
    output_dir: Path = Path("data/outputs")
    log_dir: Path = Path("logs")
    
    gemini_api_key: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

settings.attachment_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)
settings.log_dir.mkdir(parents=True, exist_ok=True)
