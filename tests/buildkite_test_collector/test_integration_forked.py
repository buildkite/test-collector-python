"""Integration tests for fork-per-test runners (pytest-forked).

pytest-forked runs each test protocol in a forked child process with
log=False, then replays the serialized reports in the parent.  The child
inherits a copy of the plugin state that is discarded on exit; only the
parent's payload is uploaded.  These tests verify that the collector
produces correct results (with execution tags, and without spurious
'no result set at finalization' warnings) in that mode.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("pytest_forked")

# pytest-forked needs py.process from the real py package.  In layered
# environments (e.g. `uv run --with pytest`), pytest's vendored py.py shim
# (py.error/py.path only) can shadow the real package, breaking pytest-forked
# itself with an INTERNALERROR — nothing our collector can be tested against.
_py = pytest.importorskip("py")
if not hasattr(_py, "process"):
    pytest.skip(
        "'py' resolves to pytest's vendored shim without py.process; "
        "pytest-forked cannot run in this environment",
        allow_module_level=True,
    )

pytestmark = pytest.mark.skipif(
    not hasattr(os, "fork"), reason="pytest-forked requires os.fork"
)


def test_forked_run_collects_results_and_tags_without_warnings(tmp_path):
    """Run pytest with --forked and verify results, tags, and clean logs."""
    test_file = Path(__file__).parent / "data" / "test_sample_execution_tag.py"
    json_output_file = tmp_path / "test_results.json"

    cmd = [
        sys.executable, "-m", "pytest",
        "--forked",
        str(test_file),
        f"--json={json_output_file}",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        pytest.fail("pytest run failed, see output above")

    output = result.stdout + result.stderr
    assert "has no result set at finalization" not in output

    with open(json_output_file, "r") as f:
        test_results = json.load(f)

    tests_by_name = {test["name"]: test for test in test_results}

    assert len(tests_by_name) == 3
    for test in test_results:
        assert test["result"] == "passed"

    assert tests_by_name["test_with_multiple_tags"]["tags"] == {
        "language.version": "3.12",
        "team": "backend",
    }
    assert tests_by_name["test_with_single_tag"]["tags"] == {"team": "frontend"}
    assert "tags" not in tests_by_name["test_without_tags"]
