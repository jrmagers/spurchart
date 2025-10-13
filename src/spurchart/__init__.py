"""Mark spurchart directory as a Python package."""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("spurchart")
except Exception:
    __version__ = "unknown"
