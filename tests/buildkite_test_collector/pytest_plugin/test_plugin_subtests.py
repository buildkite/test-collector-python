"""Tests for SubtestReport handling in the Buildkite test collector plugin.

These tests verify that the plugin correctly handles SubtestReport objects
from pytest>=9.0 built-in subtests, preventing the last-write-wins overwrite
bug described in https://github.com/buildkite/test-collector-python/issues/93.
"""

import dataclasses
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Any, Optional

import pytest

from buildkite_test_collector.collector.payload import (
    Payload,
    TestResultFailed,
    TestResultPassed,
)
from buildkite_test_collector.pytest_plugin.buildkite_plugin import (
    BuildkitePlugin,
    _is_subtest_report,
)
from _pytest.reports import TestReport


# ---------------------------------------------------------------------------
# Helpers: lightweight SubtestReport stand-in
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SubtestContext:
    """Mimics pytest.SubtestContext (pytest>=9.0)."""

    msg: Optional[str] = None
    kwargs: Mapping[str, Any] = dataclasses.field(default_factory=lambda: MappingProxyType({}))


class FakeSubtestReport(TestReport):
    """A TestReport with a ``context`` attribute, matching the duck-type
    signature of ``pytest.SubtestReport``.

    We intentionally avoid importing ``pytest.SubtestReport`` so that the
    tests can run on pytest<9.0 as well.  The plugin uses duck-typing, so
    this fake is sufficient.
    """

    def __init__(self, *, nodeid, outcome, longrepr=None, msg=None, **kwargs):
        location = ("test_file.py", 0, "test_func")
        super().__init__(
            nodeid=nodeid,
            location=location,
            keywords={},
            outcome=outcome,
            longrepr=longrepr,
            when="call",
        )
        self.context = SubtestContext(msg=msg, kwargs=MappingProxyType(kwargs))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NODEID = "tests/test_example.py::test_with_subtests"
LOCATION = ("tests/test_example.py", 10, "test_with_subtests")


@pytest.fixture
def plugin(fake_env):
    """A fresh BuildkitePlugin with the parent test already in-flight."""
    payload = Payload.init(fake_env)
    p = BuildkitePlugin(payload)
    p.pytest_runtest_logstart(NODEID, LOCATION)
    return p


# ---------------------------------------------------------------------------
# Detection helper
# ---------------------------------------------------------------------------

class TestIsSubtestReport:
    """Tests for _is_subtest_report() duck-type detection."""

    def test_detects_fake_subtest_report(self):
        report = FakeSubtestReport(nodeid=NODEID, outcome="passed", msg="hello")
        assert _is_subtest_report(report) is True

    def test_rejects_plain_test_report(self):
        report = TestReport(
            nodeid=NODEID,
            location=LOCATION,
            keywords={},
            outcome="passed",
            longrepr=None,
            when="call",
        )
        assert _is_subtest_report(report) is False

    def test_rejects_report_with_unrelated_context(self):
        """An object with a ``context`` that lacks ``msg``/``kwargs``."""
        report = TestReport(
            nodeid=NODEID,
            location=LOCATION,
            keywords={},
            outcome="passed",
            longrepr=None,
            when="call",
        )
        report.context = "some string"  # not the right shape
        assert _is_subtest_report(report) is False


# ---------------------------------------------------------------------------
# Core behaviour
# ---------------------------------------------------------------------------

class TestSubtestFailurePropagation:
    """A failed SubtestReport must mark the parent test as failed."""

    def test_single_subtest_failure_marks_parent_failed(self, plugin):
        sub = FakeSubtestReport(
            nodeid=NODEID,
            outcome="failed",
            longrepr="AssertionError: expected 1, got 2",
            msg="check value",
        )
        plugin.pytest_runtest_logreport(sub)

        test_data = plugin.in_flight[NODEID]
        assert isinstance(test_data.result, TestResultFailed)
        assert test_data.result.failure_reason == "AssertionError: expected 1, got 2"

    def test_multiple_subtest_failures_keep_parent_failed(self, plugin):
        """When multiple subtests fail, the parent stays failed."""
        sub1 = FakeSubtestReport(
            nodeid=NODEID,
            outcome="failed",
            longrepr="first failure",
            msg="subtest 1",
        )
        sub2 = FakeSubtestReport(
            nodeid=NODEID,
            outcome="failed",
            longrepr="second failure",
            msg="subtest 2",
        )
        plugin.pytest_runtest_logreport(sub1)
        plugin.pytest_runtest_logreport(sub2)

        test_data = plugin.in_flight[NODEID]
        # The important invariant: it is NOT marked "passed"
        assert isinstance(test_data.result, TestResultFailed)


class TestPassedSubtestIgnored:
    """Passing subtests must not overwrite the parent's result."""

    def test_passed_subtest_does_not_set_result(self, plugin):
        sub = FakeSubtestReport(
            nodeid=NODEID,
            outcome="passed",
            msg="check something",
        )
        plugin.pytest_runtest_logreport(sub)

        test_data = plugin.in_flight[NODEID]
        # Result should still be None (initial state), not TestResultPassed
        assert test_data.result is None

    def test_passed_subtest_after_failure_preserves_failure(self, plugin):
        fail = FakeSubtestReport(
            nodeid=NODEID,
            outcome="failed",
            longrepr="boom",
            msg="bad subtest",
        )
        ok = FakeSubtestReport(
            nodeid=NODEID,
            outcome="passed",
            msg="good subtest",
        )
        plugin.pytest_runtest_logreport(fail)
        plugin.pytest_runtest_logreport(ok)

        test_data = plugin.in_flight[NODEID]
        assert isinstance(test_data.result, TestResultFailed)
        assert test_data.result.failure_reason == "boom"


class TestSkippedSubtestIgnored:
    """Skipped subtests must not overwrite the parent's result."""

    def test_skipped_subtest_does_not_set_result(self, plugin):
        sub = FakeSubtestReport(
            nodeid=NODEID,
            outcome="skipped",
            longrepr=("test_file.py", 10, "skipped"),
            msg="skip this",
        )
        plugin.pytest_runtest_logreport(sub)

        test_data = plugin.in_flight[NODEID]
        assert test_data.result is None


class TestParentReportGuard:
    """The parent test's own 'passed' call report must not overwrite a
    subtest-induced failure."""

    def test_parent_passed_does_not_overwrite_subtest_failure(self, plugin):
        # Step 1: subtest fails
        sub = FakeSubtestReport(
            nodeid=NODEID,
            outcome="failed",
            longrepr="subtest assertion failed",
            msg="failing subtest",
        )
        plugin.pytest_runtest_logreport(sub)

        # Step 2: parent's own call-phase report arrives as "passed"
        # (because the subtest context manager swallows the exception)
        parent_report = TestReport(
            nodeid=NODEID,
            location=LOCATION,
            keywords={},
            outcome="passed",
            longrepr=None,
            when="call",
        )
        plugin.pytest_runtest_logreport(parent_report)

        # The parent must still show as failed
        test_data = plugin.in_flight[NODEID]
        assert isinstance(test_data.result, TestResultFailed)
        assert test_data.result.failure_reason == "subtest assertion failed"

    def test_parent_failed_still_works_normally(self, plugin):
        """If the parent test itself fails (not via subtests), that's fine."""
        parent_report = TestReport(
            nodeid=NODEID,
            location=LOCATION,
            keywords={},
            outcome="failed",
            longrepr="parent body raised",
            when="call",
        )
        plugin.pytest_runtest_logreport(parent_report)

        test_data = plugin.in_flight[NODEID]
        assert isinstance(test_data.result, TestResultFailed)
        assert test_data.result.failure_reason == "parent body raised"

    def test_teardown_failure_still_overrides(self, plugin):
        """A teardown failure should still override a passed call result,
        even when subtests are not involved."""
        call_report = TestReport(
            nodeid=NODEID,
            location=LOCATION,
            keywords={},
            outcome="passed",
            longrepr=None,
            when="call",
        )
        plugin.pytest_runtest_logreport(call_report)

        teardown_report = TestReport(
            nodeid=NODEID,
            location=LOCATION,
            keywords={},
            outcome="failed",
            longrepr="teardown exploded",
            when="teardown",
        )
        plugin.pytest_runtest_logreport(teardown_report)

        test_data = plugin.in_flight[NODEID]
        assert isinstance(test_data.result, TestResultFailed)

    def test_teardown_failure_overrides_subtest_failure(self, plugin):
        """If subtests failed AND teardown failed, teardown failure wins
        (consistent with existing behaviour where teardown overrides call)."""
        sub = FakeSubtestReport(
            nodeid=NODEID,
            outcome="failed",
            longrepr="subtest boom",
            msg="bad",
        )
        plugin.pytest_runtest_logreport(sub)

        # Parent call arrives as "passed" — blocked by guard
        call_report = TestReport(
            nodeid=NODEID,
            location=LOCATION,
            keywords={},
            outcome="passed",
            longrepr=None,
            when="call",
        )
        plugin.pytest_runtest_logreport(call_report)

        # Teardown fails — this should still go through (it's a real failure)
        teardown_report = TestReport(
            nodeid=NODEID,
            location=LOCATION,
            keywords={},
            outcome="failed",
            longrepr="teardown also exploded",
            when="teardown",
        )
        plugin.pytest_runtest_logreport(teardown_report)

        test_data = plugin.in_flight[NODEID]
        assert isinstance(test_data.result, TestResultFailed)
        assert test_data.result.failure_reason == "teardown also exploded"


class TestFinalizeCleanup:
    """finalize_test should clean up subtest tracking state."""

    def test_finalize_clears_subtest_tracking(self, plugin):
        sub = FakeSubtestReport(
            nodeid=NODEID,
            outcome="failed",
            longrepr="boom",
            msg="fail",
        )
        plugin.pytest_runtest_logreport(sub)
        assert NODEID in plugin._failed_by_subtest

        plugin.finalize_test(NODEID)

        assert NODEID not in plugin._failed_by_subtest
        assert NODEID not in plugin.in_flight

    def test_finalize_without_subtests_is_noop_for_tracking(self, plugin):
        """finalize_test works normally when no subtests were involved."""
        call_report = TestReport(
            nodeid=NODEID,
            location=LOCATION,
            keywords={},
            outcome="passed",
            longrepr=None,
            when="call",
        )
        plugin.pytest_runtest_logreport(call_report)

        assert NODEID not in plugin._failed_by_subtest
        result = plugin.finalize_test(NODEID)
        assert result is True
        assert NODEID not in plugin.in_flight


class TestEndToEndJsonOutput:
    """Verify that the JSON output correctly reflects subtest failures."""

    def test_failed_subtest_produces_failed_json_entry(self, plugin, tmp_path):
        # Subtest fails
        sub = FakeSubtestReport(
            nodeid=NODEID,
            outcome="failed",
            longrepr="assert 1 == 2",
            msg="value check",
        )
        plugin.pytest_runtest_logreport(sub)

        # Parent "passes"
        parent = TestReport(
            nodeid=NODEID,
            location=LOCATION,
            keywords={},
            outcome="passed",
            longrepr=None,
            when="call",
        )
        plugin.pytest_runtest_logreport(parent)

        # Finalize
        plugin.finalize_test(NODEID)

        # Write JSON
        path = tmp_path / "results.json"
        plugin.save_payload_as_json(str(path))

        import json
        results = json.loads(path.read_text())

        assert len(results) == 1
        entry = results[0]
        assert entry["result"] == "failed"
        assert entry["failure_reason"] == "assert 1 == 2"
        assert entry["scope"] == "tests/test_example.py"
        assert entry["name"] == "test_with_subtests"

    def test_all_subtests_pass_produces_passed_json_entry(self, plugin, tmp_path):
        # Two passing subtests
        for msg in ("check A", "check B"):
            sub = FakeSubtestReport(nodeid=NODEID, outcome="passed", msg=msg)
            plugin.pytest_runtest_logreport(sub)

        # Parent passes
        parent = TestReport(
            nodeid=NODEID,
            location=LOCATION,
            keywords={},
            outcome="passed",
            longrepr=None,
            when="call",
        )
        plugin.pytest_runtest_logreport(parent)

        plugin.finalize_test(NODEID)

        path = tmp_path / "results.json"
        plugin.save_payload_as_json(str(path))

        import json
        results = json.loads(path.read_text())

        assert len(results) == 1
        assert results[0]["result"] == "passed"


class TestNoSubtestsRegression:
    """Verify zero behaviour change when subtests are not used."""

    def test_simple_pass_unchanged(self, plugin):
        report = TestReport(
            nodeid=NODEID,
            location=LOCATION,
            keywords={},
            outcome="passed",
            longrepr=None,
            when="call",
        )
        plugin.pytest_runtest_logreport(report)

        test_data = plugin.in_flight[NODEID]
        assert isinstance(test_data.result, TestResultPassed)

    def test_simple_fail_unchanged(self, plugin):
        report = TestReport(
            nodeid=NODEID,
            location=LOCATION,
            keywords={},
            outcome="failed",
            longrepr="plain failure",
            when="call",
        )
        plugin.pytest_runtest_logreport(report)

        test_data = plugin.in_flight[NODEID]
        assert isinstance(test_data.result, TestResultFailed)
        assert test_data.result.failure_reason == "plain failure"

    def test_setup_failure_unchanged(self, plugin):
        report = TestReport(
            nodeid=NODEID,
            location=LOCATION,
            keywords={},
            outcome="failed",
            longrepr="fixture exploded",
            when="setup",
        )
        plugin.pytest_runtest_logreport(report)

        test_data = plugin.in_flight[NODEID]
        assert isinstance(test_data.result, TestResultFailed)
