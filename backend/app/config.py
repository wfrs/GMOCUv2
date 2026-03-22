"""Application configuration."""

import os
from pathlib import Path

APP_NAME = "GMOCU"
VERSION = "2.1.0"

# Default database location: ~/GMOCU/gmocu-v2.db
# Override with GMOCU_DATABASE env var
DATA_DIR = Path.home() / "GMOCU"
LEGACY_DATABASE_PATH = DATA_DIR / "gmocu.db"
DEFAULT_DATABASE_PATH = DATA_DIR / "gmocu-v2.db"
DATABASE_PATH = Path(os.environ.get("GMOCU_DATABASE", str(DEFAULT_DATABASE_PATH)))
