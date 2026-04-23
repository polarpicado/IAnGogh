from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(slots=True)
class AppConfig:
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    mongodb_db: str = os.getenv("MONGODB_DB", "job_hunter_master")
    app_encryption_key: str = os.getenv("APP_ENCRYPTION_KEY", "")
    app_locale: str = os.getenv("APP_LOCALE", "es")
    app_theme: str = os.getenv("APP_THEME", "dark")

    # Resolve project root from this file location to avoid cwd-dependent paths.
    base_dir: Path = Path(__file__).resolve().parents[2]
    data_dir: Path = base_dir / "data"
    contracts_dir: Path = base_dir / "contracts"


CONFIG = AppConfig()
