"""
Application Constants
Centralized configuration values to avoid magic numbers throughout the codebase.
"""

# Application Info
APP_NAME = "Local Cleaner"
APP_VERSION = "1.1.0"
APP_AUTHOR = "Emilio Ranucoli"
APP_GITHUB = "https://github.com/RanuK12/Local_CleaningPC-App"

# File Size Thresholds (in bytes)
LARGE_FILE_THRESHOLD = 500 * 1024 * 1024  # 500 MB
VERY_LARGE_FILE_THRESHOLD = 1024 * 1024 * 1024  # 1 GB
MIN_DUPLICATE_SIZE = 1024  # 1 KB - minimum size for duplicate detection

# Time Thresholds (in days)
OLD_FILE_DAYS = 730  # 2 years
VERY_OLD_FILE_DAYS = 1095  # 3 years
DEFAULT_OLD_FILE_DAYS = 180  # 6 months (configurable default)

# Scan Limits
MAX_FILES_PER_QUERY = 1000
DEFAULT_PAGE_SIZE = 100
MAX_HASH_WORKERS = 4

# UI Constants
MAX_TABLE_ROWS = 1000
PROGRESS_UPDATE_INTERVAL = 100  # ms
TOAST_DISPLAY_TIME = 3000  # ms

# Hash Settings
HASH_BLOCK_SIZE = 65536  # 64 KB
QUICK_HASH_SAMPLE_SIZE = 65536  # 64 KB from start and end

# Path Limits
MAX_PATH_LENGTH = 260  # Windows MAX_PATH
MAX_FILENAME_LENGTH = 255

# Risk Levels
RISK_LEVELS = {
    'safe': {
        'color': '#a6e3a1',  # Green
        'label': 'Seguro',
        'icon': '✅'
    },
    'low': {
        'color': '#f9e2af',  # Yellow
        'label': 'Bajo',
        'icon': '⚠️'
    },
    'medium': {
        'color': '#fab387',  # Orange
        'label': 'Medio',
        'icon': '🔶'
    },
    'high': {
        'color': '#f38ba8',  # Red
        'label': 'Alto',
        'icon': '🔴'
    }
}

# Category Colors (Catppuccin palette)
CATEGORY_COLORS = {
    'System': '#f38ba8',      # Red
    'Applications': '#89b4fa', # Blue
    'Games': '#a6e3a1',       # Green
    'Media': '#f9e2af',       # Yellow
    'Documents': '#cba6f7',   # Mauve
    'Development': '#94e2d5', # Teal
    'Downloads': '#fab387',   # Peach
    'Archives': '#89dceb',    # Sky
    'Installers': '#f5c2e7',  # Pink
    'Backups': '#74c7ec',     # Sapphire
    'Unknown': '#6c7086',     # Overlay0
}

# File Extensions by Category
TEMP_EXTENSIONS = ['.tmp', '.temp', '.bak', '.old', '.cache', '~']
ARCHIVE_EXTENSIONS = ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2']
INSTALLER_EXTENSIONS = ['.exe', '.msi', '.msix']
MEDIA_EXTENSIONS = [
    # Video
    '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
    # Audio
    '.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a',
    # Images
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico'
]
DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf']

# Browser Cache Paths (relative to user profile)
BROWSER_CACHE_PATHS = {
    'Chrome': r'AppData\Local\Google\Chrome\User Data\Default\Cache',
    'Firefox': r'AppData\Local\Mozilla\Firefox\Profiles',
    'Edge': r'AppData\Local\Microsoft\Edge\User Data\Default\Cache',
    'Opera': r'AppData\Roaming\Opera Software\Opera Stable\Cache',
    'Brave': r'AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\Cache',
}

# Windows Temp Paths
WINDOWS_TEMP_PATHS = [
    r'%TEMP%',
    r'%TMP%',
    r'C:\Windows\Temp',
    r'C:\Windows\Prefetch',
]
