# Contributing to Local Cleaner

Thank you for your interest in contributing to Local Cleaner! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- Windows 10/11 (for full functionality)
- Git

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Local_CleaningPC-App.git
   cd Local_CleaningPC-App
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python main.py
   ```

## 📋 How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/RanuK12/Local_CleaningPC-App/issues)
2. If not, create a new issue with:
   - Clear title describing the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots if applicable
   - Your Windows version and Python version

### Suggesting Features

1. Open an issue with the `enhancement` label
2. Describe the feature and why it would be useful
3. Include mockups or examples if possible

### Submitting Pull Requests

1. Create a feature branch from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the code style guidelines

3. Test your changes thoroughly

4. Commit with clear messages
   ```bash
   git commit -m "feat: add new feature description"
   ```

5. Push and create a Pull Request

## 🎨 Code Style Guidelines

### Python

- Follow PEP 8
- Use type hints where possible
- Write docstrings for all public functions/classes
- Keep functions small and focused

### Example:

```python
def format_file_size(bytes_size: int) -> str:
    """
    Format bytes to human-readable string.
    
    Args:
        bytes_size: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"
```

### Commit Messages

Use conventional commits format:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Maintenance tasks

## 📁 Project Structure

```
Local_CleaningPC-App/
├── main.py                  # Entry point
├── src/
│   ├── core/               # Business logic
│   │   ├── scanner.py      # Disk scanning
│   │   ├── analyzer.py     # File analysis
│   │   ├── categorizer.py  # File categorization
│   │   ├── cleaner.py      # Cleanup operations
│   │   └── app_analyzer.py # Installed apps
│   ├── db/                 # Database layer
│   │   ├── database.py     # SQLite operations
│   │   └── models.py       # Data models
│   ├── ui/                 # User interface
│   │   ├── main_window.py  # Main window
│   │   ├── dialogs.py      # Dialog windows
│   │   └── tabs/           # Tab widgets
│   └── utils/              # Utilities
│       ├── config.py       # Configuration
│       ├── constants.py    # App constants
│       └── logger.py       # Logging
├── resources/              # Assets
│   └── style.qss          # Qt stylesheet
├── tests/                  # Test files
└── data/                   # Runtime data
```

## 🔒 Security

- Never commit sensitive data (passwords, API keys)
- Validate all file paths before operations
- Sanitize user inputs
- Report security vulnerabilities privately

## 📝 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for helping make Local Cleaner better! 🎉
