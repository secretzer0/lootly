"""Version information for Lootly."""
import tomllib
from pathlib import Path


def get_version():
    """Get version from pyproject.toml."""
    try:
        # Find pyproject.toml by going up from current file location
        current_dir = Path(__file__).parent
        project_root = current_dir.parent  # Go up from src to project root
        pyproject_path = project_root / "pyproject.toml"
        
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            return data["project"]["version"]
    except Exception:
        # Fallback version if we can't read pyproject.toml
        return "0.1.0"


__version__ = get_version()