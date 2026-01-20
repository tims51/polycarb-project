
import os
from pathlib import Path

# Base directory of the application (app/)
APP_DIR = Path(__file__).parent
# Root directory of the project
ROOT_DIR = APP_DIR.parent

# Data paths
DATA_FILE = ROOT_DIR / "data" / "data.json"
BACKUP_DIR = ROOT_DIR / "data" / "backups"
TEMP_DIR = ROOT_DIR / "data" / "temp"

# Ensure directories exist
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Application Settings
APP_NAME = "聚羧酸减水剂研发管理系统"
APP_ICON = "🧪"
VERSION = "2.7.0"
DEFAULT_UNIT = "吨" # Avoid importing from core.enums to prevent circular import

# UI Settings
DEFAULT_FONT_SCALE = 1.0
DEFAULT_MOBILE_MODE = True

# Colors
PRIMARY_COLOR = "#FF4B4B"
BACKGROUND_COLOR = "#FFFFFF"
TEXT_COLOR = "#31333F"

# Internet Access
URL_FILE_PATH = ROOT_DIR / ".public_url"

# Logging
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"
