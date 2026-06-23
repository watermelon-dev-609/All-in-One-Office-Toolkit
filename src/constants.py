"""Application-wide constants."""

import os
from pathlib import Path

# App identity
APP_NAME = "全能办公工具箱"
APP_NAME_EN = "OmniOffice Toolkit"
APP_VERSION = "0.1.0"
APP_VERSION_TUPLE = (0, 1, 0)
APP_ORG = "OmniOffice"
APP_DOMAIN = "omnioffice.local"

# Paths
ROOT_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = ROOT_DIR / "src"
RESOURCES_DIR = ROOT_DIR / "resources"
DATA_DIR = ROOT_DIR / "data"
BUILD_DIR = ROOT_DIR / "build"
MODULES_DIR = SRC_DIR / "modules"

# Runtime data paths
CONFIG_FILE = DATA_DIR / "config.yaml"
LOG_DIR = DATA_DIR / "logs"
MODELS_DIR = DATA_DIR / "models"
TEMPLATES_DIR = DATA_DIR / "templates"

# Resource paths
I18N_DIR = RESOURCES_DIR / "i18n"
PROMPTS_DIR = RESOURCES_DIR / "prompts"
ICONS_DIR = SRC_DIR / "ui" / "resources" / "icons"
STYLES_DIR = SRC_DIR / "ui" / "styles"

# Module IDs
MODULE_IMAGE = "image_processing"
MODULE_PDF = "pdf_tools"
MODULE_OFFICE = "office_tools"
MODULE_BATCH = "batch_tools"
MODULE_EFFICIENCY = "efficiency_tools"
MODULE_AI = "ai_tools"
MODULE_MINDMAP = "mind_map"

# Output
DEFAULT_OUTPUT_SUBDIR = "Output"

# Performance
DEFAULT_MAX_THREADS = 0  # 0 = auto-detect (cpu_count - 1)
DEFAULT_MAX_MEMORY_MB = 2048

# Supported formats
IMAGE_FORMATS_INPUT = [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif", ".ico"]
IMAGE_FORMATS_OUTPUT = [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"]
PDF_FORMATS = [".pdf"]
WORD_FORMATS = [".docx"]
EXCEL_FORMATS = [".xlsx", ".xlsm", ".csv"]
PPT_FORMATS = [".pptx"]
ARCHIVE_FORMATS = [".zip", ".7z", ".tar", ".gz", ".bz2"]
