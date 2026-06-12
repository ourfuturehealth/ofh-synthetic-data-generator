"""Synthetic data generation tools for Our Future Health-style questionnaire data."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("ofh-synthetic-data")
except PackageNotFoundError:
    __version__ = "0.0.0"
