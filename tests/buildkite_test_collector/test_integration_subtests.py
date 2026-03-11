"""Integration test: run a real pytest subprocess with subtests and verify JSON output.

This mirrors the existing test_integration.py pattern in the repo — it
invokes pytest in a subprocess with ``--json=<path>`` and inspects the
resulting JSON file.

Requires pytest>=9.0 for built-in subtests support.  The test is
automatically skipped on older pytest versions.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


SAMPLE_FILE = Path(__file__).parent / "data" / "test_sample_subtests.py"

# Check if pytest>=9.0 is available (needed for built-in subtests)
_pytest_version = tuple(int(x) for x in pytest.__version__.split(".")[:2])
_has_builtin_subtests = _pytest_version >= (9, 0)


@pytest.mark.skipif(
    not _has_builtin_subtests,
    reason=f"pytest>=9.0 required for built-in subtests (have {pytest.__version__})",
)
class TestSubtestIntegration:
    """End-to-end: pytest subprocess -> collector -> JSON file -> assertions."""

    def _run_pytest(self, tmp_path, *extra_args):
        json_output = tmp_path / "results.json"
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(SAMPLE_FILE),
            f"--json={json_output}",
            "-v",
            *extra_args,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result, json_output

    def test_mixed_subtests_reported_as_failed(self, tmp_path):
        """A test with mixed pass/fail subtests must appear as 'failed'."""
        result, json_output = self._run_pytest(tmp_path, "-k", "test_mixed_subtests")

        # pytest itself should exit non-zero (there is a subtest failure)
        assert result.returncode != 0, f"Expected failure, got:\n{result.stdout}"

        assert json_output.exists(), f"JSON not created. stderr:\n{result.stderr}"
        data = json.loads(json_output.read_text())

        tests_by_name = {t["name"]: t for t in data}
        assert "test_mixed_subtests" in tests_by_name

        entry = tests_by_name["test_mixed_subtests"]
        assert entry["result"] == "failed", (
            f"Expected 'failed' but got '{entry['result']}'. "
            "The subtest failure was not propagated to the parent test."
        )
        assert entry["failure_reason"] is not None

    def test_all_subtests_pass_reported_as_passed(self, tmp_path):
        """A test where all subtests pass should appear as 'passed'."""
        result, json_output = self._run_pytest(tmp_path, "-k", "test_all_subtests_pass")

        assert result.returncode == 0, f"Unexpected failure:\n{result.stdout}"
        assert json_output.exists()

        data = json.loads(json_output.read_text())
        tests_by_name = {t["name"]: t for t in data}
        assert "test_all_subtests_pass" in tests_by_name

        entry = tests_by_name["test_all_subtests_pass"]
        assert entry["result"] == "passed"

    def test_plain_test_unaffected(self, tmp_path):
        """A test with no subtests should work exactly as before."""
        result, json_output = self._run_pytest(tmp_path, "-k", "test_no_subtests")

        assert result.returncode == 0, f"Unexpected failure:\n{result.stdout}"
        assert json_output.exists()

        data = json.loads(json_output.read_text())
        tests_by_name = {t["name"]: t for t in data}
        assert "test_no_subtests" in tests_by_name

        entry = tests_by_name["test_no_subtests"]
        assert entry["result"] == "passed"

    def test_full_run_correct_count_and_results(self, tmp_path):
        """Run all three sample tests. Verify counts and per-test results."""
        result, json_output = self._run_pytest(tmp_path)

        # One test fails, so pytest exits non-zero
        assert result.returncode != 0

        data = json.loads(json_output.read_text())
        tests_by_name = {t["name"]: t for t in data}

        # Should have exactly 3 test entries (one per test function)
        assert len(data) == 3, (
            f"Expected 3 entries, got {len(data)}: {list(tests_by_name.keys())}"
        )

        assert tests_by_name["test_mixed_subtests"]["result"] == "failed"
        assert tests_by_name["test_all_subtests_pass"]["result"] == "passed"
        assert tests_by_name["test_no_subtests"]["result"] == "passed"

    def test_json_nodeids_are_real_pytest_nodeids(self, tmp_path):
        """The scope::name in JSON must be a valid pytest nodeid — no
        synthetic subtest names that would break bktec retries."""
        result, json_output = self._run_pytest(tmp_path)

        data = json.loads(json_output.read_text())

        for entry in data:
            # Reconstructed nodeid must match standard pytest format
            reconstructed = f"{entry['scope']}::{entry['name']}"
            assert "::" in reconstructed
            # Must not contain subtest message fragments
            assert "[" not in entry["name"], (
                f"Synthetic subtest name leaked into JSON: {entry['name']}"
            )
            assert "(<subtest>)" not in entry["name"]
