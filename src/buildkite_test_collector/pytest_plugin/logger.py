"""A plugin internal logger, use DEBUG=1 env var to turn on all debug logs"""
import os
import logging

def setup_logger(name=__name__):
    """
    Configure and return a logger with the specified name.

    The logger's level is set based on the DEBUG environment variable.
    If DEBUG=1, the level is set to DEBUG, otherwise it's set to INFO.

    Args:
        name (str): The name for the logger. Defaults to the current module name.

    Returns:
        logging.Logger: A configured logger instance.
    """
    l = logging.getLogger(name)

    # Set level based on DEBUG env var
    l.setLevel(logging.DEBUG if os.getenv("DEBUG") == "1" else logging.INFO)

    # Add handler only if none exists (prevents duplicate logs)
    if not l.handlers:
        handler = logging.StreamHandler()  # Log to console
        formatter = logging.Formatter(
            "%(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        l.addHandler(handler)

    # Optional: Stop propagation to root logger
    l.propagate = False

    return l

# Example default logger (optional)
logger = setup_logger("buildkite-test-collector")
