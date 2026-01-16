import re
from pathlib import Path
from typing import Tuple, List, Dict
from enum import Enum


class Category(Enum):
    # Main categories with friendly names
    SYSTEM = "System"
    APPLICATIONS = "Applications"
    GAMES = "Games"
    MEDIA = "Media"
    DOCUMENTS = "Documents"
    DEVELOPMENT = "Development"
    DOWNLOADS = "Downloads"
    ARCHIVES = "Archives"
    INSTALLERS = "Installers"
    BACKUPS = "Backups"
    UNKNOWN = "Unknown"


class CategoryConfidence(Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class FileCategorizer:
    """
    Intelligently categorizes files and folders based on heuristics.
    Each categorization includes confidence level and explanation of rules fired.
    """

    # System paths and patterns that indicate category
    SYSTEM_PATTERNS = {
        "paths": [
            r"^[A-Z]:\\Windows",
            r"^[A-Z]:\\System",
            r"\\System32\\",
            r"\\SysWOW64\\",
            r"^[A-Z]:\\Recovery",
            r"^[A-Z]:\\ProgramData",
            r"\\$Recycle.Bin",
        ],
        "extensions": [".sys", ".drv", ".inf", ".cat", ".msi"],
    }

    APPS_PATTERNS = {
        "paths": [
            r"^[A-Z]:\\Program Files",
            r"^[A-Z]:\\Program Files \(x86\)",
            r"\\AppData\\Local\\Programs",
            r"\\AppData\\Roaming",
        ],
        "extensions": [],
    }

    GAMES_PATTERNS = {
        "paths": [
            r"Steam",
            r"Epic Games",
            r"Battle\.net",
            r"Xbox",
            r"GOG",
            r"\\Games",
            r"\\Juegos",
        ],
        "extensions": [],
    }

    MEDIA_PATTERNS = {
        "extensions": [
            ".mp3", ".wav", ".flac", ".aac", ".ogg",  # Audio
            ".mp4", ".avi", ".mkv", ".mov", ".flv", ".wmv",  # Video
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff",  # Images
            ".psd", ".ai", ".svg",  # Design
        ],
        "paths": [r"\\Pictures", r"\\Music", r"\\Videos", r"\\Fotos", r"\\Música"],
    }

    DOCUMENTS_PATTERNS = {
        "extensions": [
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            ".txt", ".md", ".odt", ".ods", ".rtf",
        ],
        "paths": [r"\\Documents", r"\\Desktop"],
    }

    DEV_PATTERNS = {
        "paths": [
            r"\\node_modules",
            r"\\.venv",
            r"\\venv",
            r"\\env",
            r"\\.git",
            r"\\dist",
            r"\\build",
            r"\\bin",
            r"\\obj",
            r"\\target",
            r"\\.gradle",
            r"\\__pycache__",
            r"\\\.idea",
            r"\\.vs",
            r"\\\.vscode",
            r"repo",
            r"repo git",
            r"\\src\\",
        ],
        "extensions": [
            ".py", ".js", ".ts", ".java", ".cpp", ".cs", ".go", ".rs",
            ".gradle", ".maven", ".sln", ".vcxproj",
        ],
    }

    DOWNLOADS_PATTERNS = {
        "paths": [r"\\Downloads", r"\\Descargas"],
        "extensions": [],
    }

    ARCHIVES_PATTERNS = {
        "extensions": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".iso"],
    }

    INSTALLERS_PATTERNS = {
        "extensions": [".exe", ".msi", ".app", ".deb", ".rpm"],
    }

    BACKUPS_PATTERNS = {
        "paths": [r"\\Backup", r"\\Backups", r"\\backup"],
        "extensions": [".iso", ".img", ".bak", ".backup", ".vhd", ".vmdk"],
    }

    def __init__(self, custom_rules: Dict = None):
        # custom_rules allows user to override/extend default rules
        self.custom_rules = custom_rules or {}
        self.rules_fired = []

    def categorize(self, file_path: str, is_directory: bool = False) -> Tuple[Category, CategoryConfidence, List[str]]:
        """
        Categorize a file or directory.
        
        Returns:
            Tuple of (Category, Confidence, list of rules that matched)
        """
        self.rules_fired = []
        path_obj = Path(file_path)
        path_lower = str(file_path).lower()
        name_lower = path_obj.name.lower()
        ext_lower = path_obj.suffix.lower()

        # Check custom rules first (user overrides have priority)
        if self.custom_rules:
            result = self._check_custom_rules(file_path)
            if result:
                return result

        # System check (highest priority, usually critical)
        result = self._check_category(
            path_lower, ext_lower, name_lower,
            Category.SYSTEM, self.SYSTEM_PATTERNS
        )
        if result and result[0] == Category.SYSTEM:
            return (result[0], CategoryConfidence.HIGH, self.rules_fired)

        # Backups (images, ISOs, etc.)
        result = self._check_category(
            path_lower, ext_lower, name_lower,
            Category.BACKUPS, self.BACKUPS_PATTERNS
        )
        if result:
            return (result[0], CategoryConfidence.HIGH, self.rules_fired)

        # Games (distinct from apps)
        result = self._check_category(
            path_lower, ext_lower, name_lower,
            Category.GAMES, self.GAMES_PATTERNS
        )
        if result:
            return (result[0], CategoryConfidence.HIGH, self.rules_fired)

        # Development (specific tools and folders)
        result = self._check_category(
            path_lower, ext_lower, name_lower,
            Category.DEVELOPMENT, self.DEV_PATTERNS
        )
        if result:
            return (result[0], CategoryConfidence.MEDIUM, self.rules_fired)

        # Media (large files, specific extensions)
        result = self._check_category(
            path_lower, ext_lower, name_lower,
            Category.MEDIA, self.MEDIA_PATTERNS
        )
        if result:
            return (result[0], CategoryConfidence.HIGH, self.rules_fired)

        # Downloads folder (but not all downloads)
        result = self._check_category(
            path_lower, ext_lower, name_lower,
            Category.DOWNLOADS, self.DOWNLOADS_PATTERNS
        )
        if result and not is_directory:
            return (result[0], CategoryConfidence.MEDIUM, self.rules_fired)

        # Installers
        result = self._check_category(
            path_lower, ext_lower, name_lower,
            Category.INSTALLERS, self.INSTALLERS_PATTERNS
        )
        if result:
            return (result[0], CategoryConfidence.HIGH, self.rules_fired)

        # Archives
        result = self._check_category(
            path_lower, ext_lower, name_lower,
            Category.ARCHIVES, self.ARCHIVES_PATTERNS
        )
        if result:
            return (result[0], CategoryConfidence.MEDIUM, self.rules_fired)

        # Documents
        result = self._check_category(
            path_lower, ext_lower, name_lower,
            Category.DOCUMENTS, self.DOCUMENTS_PATTERNS
        )
        if result:
            return (result[0], CategoryConfidence.HIGH, self.rules_fired)

        # Applications (more general)
        result = self._check_category(
            path_lower, ext_lower, name_lower,
            Category.APPLICATIONS, self.APPS_PATTERNS
        )
        if result:
            return (result[0], CategoryConfidence.MEDIUM, self.rules_fired)

        # Fallback
        return (Category.UNKNOWN, CategoryConfidence.LOW, self.rules_fired)

    def _check_category(self, path_lower: str, ext_lower: str, name_lower: str,
                       category: Category, patterns: Dict) -> Tuple[Category, CategoryConfidence, List[str]]:
        """Check if file matches patterns for a given category."""
        matched = False

        # Check path patterns
        if "paths" in patterns:
            for pattern in patterns["paths"]:
                if re.search(pattern, path_lower, re.IGNORECASE):
                    self.rules_fired.append(f"Path pattern: {pattern}")
                    matched = True
                    break

        # Check extension patterns
        if not matched and "extensions" in patterns:
            for ext in patterns["extensions"]:
                if ext_lower == ext.lower():
                    self.rules_fired.append(f"Extension: {ext}")
                    matched = True
                    break

        if matched:
            return (category, CategoryConfidence.HIGH, self.rules_fired)

        return None

    def _check_custom_rules(self, file_path: str) -> Tuple[Category, CategoryConfidence, List[str]]:
        """Check user-defined custom categorization rules."""
        path_lower = str(file_path).lower()

        for rule_name, rule_config in self.custom_rules.items():
            if "pattern" in rule_config:
                pattern = rule_config["pattern"]
                if re.search(pattern, path_lower, re.IGNORECASE):
                    category_str = rule_config.get("category", "Unknown")
                    try:
                        category = Category[category_str.upper()]
                    except KeyError:
                        category = Category.UNKNOWN
                    self.rules_fired.append(f"Custom rule: {rule_name}")
                    return (category, CategoryConfidence.HIGH, self.rules_fired)

        return None

    @staticmethod
    def get_category_display_name(category: Category) -> str:
        """Return user-friendly name for category."""
        return category.value

    @staticmethod
    def get_all_categories() -> List[str]:
        """Return list of all available category names."""
        return [c.value for c in Category]
