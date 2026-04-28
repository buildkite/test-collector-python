"""Sample test file with an import error.

This file deliberately imports a non-existent module to trigger a collection
error in pytest — the same scenario as importing a removed/renamed symbol
from a real package.
"""

from nonexistent_module import does_not_exist


def test_should_be_reported_as_failed():
    """This test can never run, but should still appear as a failure in the report."""
    assert does_not_exist() == 42
