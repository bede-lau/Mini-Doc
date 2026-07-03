"""EvidenceOS Mini core package.

Re-exports the public surface used by the API, scripts, and benchmark runner.
Keep this the single import entry point so downstream code does not reach into
private module paths.
"""

from packages.core.config import Settings, get_settings

__all__ = ["Settings", "get_settings"]
__version__ = "0.1.0"
