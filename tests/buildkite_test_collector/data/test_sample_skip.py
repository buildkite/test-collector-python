"""Sample test file used by the integration test.

This file exercises various skip mechanisms and is run in a subprocess
by test_integration_skip.py to verify the JSON output contains
"result": "skipped" for each case.
"""

import pytest


@pytest.mark.skip(reason="unconditional skip")
def test_skip_marker():
    """Skipped via @pytest.mark.skip — skip happens during setup."""
    assert False  # noqa: B011 -- should never run


@pytest.mark.skipif(True, reason="condition is true")
def test_skipif_marker():
    """Skipped via @pytest.mark.skipif — skip happens during setup."""
    assert False  # noqa: B011 -- should never run


@pytest.fixture
def skip_fixture():
    pytest.skip("skipped in fixture")


def test_skip_in_fixture(skip_fixture):
    """Skipped via pytest.skip() inside a fixture — skip happens during setup."""
    assert False  # noqa: B011 -- should never run


def test_skip_inline():
    """Skipped via pytest.skip() in the test body — skip happens during call."""
    pytest.skip("inline skip")


def test_passing():
    """A normal passing test to verify we don't break non-skipped tests."""
    assert True
