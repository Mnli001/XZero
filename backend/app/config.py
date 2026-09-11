"""Central settings (env-driven, pydantic-settings)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Project Zero"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    database_url: str = "sqlite:///./data/xzero.db"
    cors_origins: str = "*"

    mt5_mode: str = "mock"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    default_risk_pct: float = 2.0
    max_risk_pct: float = 5.0
    circuit_max_consec_losses: int = 2
    circuit_lock_hours: int = 24
    allow_circuit_reset: bool = True  # MUST be false in production

    knowledge_dir: str = "./data/knowledge"
    reports_dir: str = "./data/reports"
    journal_path: str = "./data/journal.jsonl"
    circuit_path: str = "./data/circuit_breaker.json"

    default_symbol: str = "EURUSD"
    default_timeframe: str = "M5"


settings = Settings()
