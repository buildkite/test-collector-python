"""Sample test file used by the integration test.

This file exercises pytest>=9.0 built-in subtests and is run in a subprocess
by test_integration_subtests.py to verify the JSON output.
"""


def test_mixed_subtests(subtests):
    """A test where some subtests pass and one fails."""
    with subtests.test(msg="passing check 1"):
        assert 1 + 1 == 2

    with subtests.test(msg="failing check"):
        assert 1 + 1 == 3  # noqa: PLR0133 -- intentional failure

    with subtests.test(msg="passing check 2"):
        assert 2 + 2 == 4


def test_all_subtests_pass(subtests):
    """A test where all subtests pass."""
    with subtests.test(msg="alpha"):
        assert True

    with subtests.test(msg="beta"):
        assert True


def test_no_subtests():
    """A plain test with no subtests — should be unaffected."""
    assert 42 == 42
