from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "llm-auditor-service"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    ollama_timeout_seconds: float = 30.0
    ollama_retries: int = 1
    ollama_temperature: float = 0.0
    log_level: str = "INFO"
    log_dir: str = "logs"
    log_file: str = Field(default="llm_service.log")

    model_config = SettingsConfigDict(
        env_prefix="LLM_SERVICE_",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    configure_logging(settings)
    return settings


def configure_logging(settings: Settings) -> None:
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / settings.log_file

    logger = logging.getLogger("llm_service")
    if logger.handlers:
        return

    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False


def generate_request_id() -> str:
    return uuid4().hex
