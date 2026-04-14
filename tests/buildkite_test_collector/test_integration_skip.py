"""Integration test: run a real pytest subprocess with skipped tests and verify JSON output.

This exercises the fix for tests skipped during the setup phase (e.g.
@pytest.mark.skip, @pytest.mark.skipif, pytest.skip() in fixtures)
which previously produced JSON with no "result" key.

See: https://github.com/buildkite/test-engine-client/issues/464
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


SAMPLE_FILE = Path(__file__).parent / "data" / "test_sample_skip.py"


class TestSkipIntegration:
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

    def test_all_tests_have_result_key(self, tmp_path):
        """Every test in the JSON output must have a 'result' key."""
        result, json_output = self._run_pytest(tmp_path)

        assert json_output.exists(), f"JSON not created. stderr:\n{result.stderr}"
        data = json.loads(json_output.read_text())

        for entry in data:
            assert "result" in entry, (
                f"Test {entry['name']} is missing the 'result' key — "
                "this causes test-engine-client to treat it as unknown."
            )

    def test_skip_marker_reported_as_skipped(self, tmp_path):
        """@pytest.mark.skip produces 'result': 'skipped'."""
        result, json_output = self._run_pytest(tmp_path, "-k", "test_skip_marker")

        data = json.loads(json_output.read_text())
        tests_by_name = {t["name"]: t for t in data}

        assert tests_by_name["test_skip_marker"]["result"] == "skipped"

    def test_skipif_marker_reported_as_skipped(self, tmp_path):
        """@pytest.mark.skipif produces 'result': 'skipped'."""
        result, json_output = self._run_pytest(tmp_path, "-k", "test_skipif_marker")

        data = json.loads(json_output.read_text())
        tests_by_name = {t["name"]: t for t in data}

        assert tests_by_name["test_skipif_marker"]["result"] == "skipped"

    def test_skip_in_fixture_reported_as_skipped(self, tmp_path):
        """pytest.skip() in a fixture produces 'result': 'skipped'."""
        result, json_output = self._run_pytest(tmp_path, "-k", "test_skip_in_fixture")

        data = json.loads(json_output.read_text())
        tests_by_name = {t["name"]: t for t in data}

        assert tests_by_name["test_skip_in_fixture"]["result"] == "skipped"

    def test_skip_inline_reported_as_skipped(self, tmp_path):
        """pytest.skip() in the test body produces 'result': 'skipped'."""
        result, json_output = self._run_pytest(tmp_path, "-k", "test_skip_inline")

        data = json.loads(json_output.read_text())
        tests_by_name = {t["name"]: t for t in data}

        assert tests_by_name["test_skip_inline"]["result"] == "skipped"

    def test_passing_test_unaffected(self, tmp_path):
        """A normal passing test still works."""
        result, json_output = self._run_pytest(tmp_path, "-k", "test_passing")

        data = json.loads(json_output.read_text())
        tests_by_name = {t["name"]: t for t in data}

        assert tests_by_name["test_passing"]["result"] == "passed"

    def test_full_run_correct_results(self, tmp_path):
        """Run all sample tests. Verify counts and per-test results."""
        result, json_output = self._run_pytest(tmp_path)

        data = json.loads(json_output.read_text())
        tests_by_name = {t["name"]: t for t in data}

        assert len(data) == 5, (
            f"Expected 5 entries, got {len(data)}: {list(tests_by_name.keys())}"
        )

        assert tests_by_name["test_skip_marker"]["result"] == "skipped"
        assert tests_by_name["test_skipif_marker"]["result"] == "skipped"
        assert tests_by_name["test_skip_in_fixture"]["result"] == "skipped"
        assert tests_by_name["test_skip_inline"]["result"] == "skipped"
        assert tests_by_name["test_passing"]["result"] == "passed"
