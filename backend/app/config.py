"""Application configuration."""

import os
from pathlib import Path

APP_NAME = "GMOCU"
VERSION = "2.0.0"

# Default database location: ~/GMOCU/gmocu.db
# Override with GMOCU_DATABASE env var
DATA_DIR = Path.home() / "GMOCU"
DATABASE_PATH = Path(os.environ.get("GMOCU_DATABASE", str(DATA_DIR / "gmocu.db")))
