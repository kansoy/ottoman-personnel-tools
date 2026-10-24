"""Deterministic helpers for source-grounded personnel extraction.

Semantic extraction is performed by the hosting model or a human reader.
This package prepares sources, checks citations and exports supplied readings.
"""

__version__ = "0.1.1"

from .intake import prepare_source
from .validation import validate_records
from .export import export_records

__all__ = ["prepare_source", "validate_records", "export_records", "__version__"]
