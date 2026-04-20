"""Integration test: collection errors (import failures) are captured in the JSON report.

When a test file has an import error, pytest fails during collection. The
``pytest_collectreport`` hook on ``BuildkitePlugin`` captures the error and
adds it to the JSON report as a failed test entry.

See: https://github.com/buildkite/test-collector-python/issues/106
"""

import json
import subprocess
import sys
from pathlib import Path


BROKEN_FILE = Path(__file__).parent / "data" / "test_sample_import_error.py"
PASSING_FILE = Path(__file__).parent / "data" / "test_sample_skip.py"


class TestImportErrorReporting:
    """Verify that import errors are captured in the JSON report."""

    def _run_pytest(self, tmp_path, test_files, *extra_args):
        json_output = tmp_path / "results.json"
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            *[str(f) for f in test_files],
            f"--json={json_output}",
            "-v",
            *extra_args,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result, json_output

    def test_pytest_exits_nonzero_on_import_error(self, tmp_path):
        """Pytest itself correctly detects the import error and exits non-zero."""
        result, _ = self._run_pytest(tmp_path, [BROKEN_FILE])

        assert result.returncode != 0, (
            "pytest should exit non-zero when a test file has an import error"
        )
        assert "ModuleNotFoundError" in result.stdout, (
            "pytest output should mention the import error"
        )

    def test_import_error_captured_in_json_report(self, tmp_path):
        """The JSON report captures the collection error as a failed test."""
        result, json_output = self._run_pytest(tmp_path, [BROKEN_FILE])

        assert result.returncode != 0

        assert json_output.exists(), f"JSON not created. stderr:\n{result.stderr}"
        data = json.loads(json_output.read_text())

        assert len(data) == 1, (
            f"Expected 1 entry for the collection error, got {len(data)}: "
            f"{[t.get('name') for t in data]}"
        )

        entry = data[0]
        assert entry["result"] == "failed"
        assert entry.get("failure_reason") is not None, "failure_reason should be present"
        assert "ImportError" in entry["failure_reason"]

    def test_import_error_reported_alongside_passing_tests(self, tmp_path):
        """With --continue-on-collection-errors, both passing tests and the
        collection error appear in the report."""
        result, json_output = self._run_pytest(
            tmp_path,
            [BROKEN_FILE, PASSING_FILE],
            "--continue-on-collection-errors",
        )

        assert result.returncode != 0, "pytest should still exit non-zero"

        data = json.loads(json_output.read_text())
        names = [t["name"] for t in data]

        # 5 tests from test_sample_skip.py + 1 collection error from test_sample_import_error.py
        assert len(data) == 6, (
            f"Expected 6 entries (5 passing + 1 collection error), got {len(data)}: {names}"
        )

        assert "test_passing" in names

        failed = [t for t in data if t["result"] == "failed"]
        assert len(failed) == 1
        assert failed[0].get("failure_reason") is not None, "failure_reason should be present"
        assert "ImportError" in failed[0]["failure_reason"]
