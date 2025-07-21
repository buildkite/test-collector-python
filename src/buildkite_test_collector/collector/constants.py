# constants.py

"""This module defines collector-level constants."""

DISTRIBUTION_NAME = 'buildkite-test-collector'
COLLECTOR_NAME = f"python-{DISTRIBUTION_NAME}"

try:
    from importlib.metadata import version, PackageNotFoundError
    try:
        VERSION = version(DISTRIBUTION_NAME)
    except PackageNotFoundError:
        # Fallback for development environments where package isn't installed
        VERSION = 'dev'
except ImportError:
    # Fallback for edge cases
    VERSION = 'unknown'
