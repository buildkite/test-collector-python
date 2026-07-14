import json
import os
from types import SimpleNamespace

import pytest

from buildkite_test_collector.collector.payload import Payload, TestData, TestResultFailed, TestResultPassed, TestResultSkipped
from buildkite_test_collector.pytest_plugin import BuildkitePlugin

from _pytest._code.code import ExceptionInfo
from _pytest.reports import CollectReport, TestReport

def test_runtest_logstart_with_unstarted_payload(fake_env):
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    assert plugin.payload.started_at is None

    plugin.pytest_runtest_logstart("wat::when", [1, 2])

    assert plugin.payload.started_at is not None


def test_pytest_runtest_logreport_simple_pass(fake_env):
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    location = ("", None, "")
    report = TestReport(nodeid="", location=location, keywords={}, outcome="passed", longrepr=None, when="call")

    plugin.pytest_runtest_logstart(report.nodeid, location)
    plugin.pytest_runtest_logreport(report)

    test_data = plugin.in_flight.get(report.nodeid)
    assert test_data is not None

    assert isinstance(test_data.result, TestResultPassed)


def test_pytest_runtest_logreport_fail_oneline(fake_env):
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    location = ("", None, "")
    longrepr = "the reason the test failed"
    report = TestReport(nodeid="", location=location, keywords={}, outcome="failed", longrepr=longrepr, when="call")

    plugin.pytest_runtest_logstart(report.nodeid, location)
    plugin.pytest_runtest_logreport(report)
    test_data = plugin.in_flight.get(report.nodeid)
    plugin.pytest_runtest_logfinish(report.nodeid, location)

    assert isinstance(test_data, TestData)
    assert isinstance(test_data.result, TestResultFailed)
    assert test_data.result.failure_reason == "the reason the test failed"


def test_pytest_runtest_logreport_fail_multiline(fake_env):
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    location = ("", None, "")
    longrepr = "the reason the test failed\n.. is quite complicated\nso here is more detail"
    report = TestReport(nodeid="", location=location, keywords={}, outcome="failed", longrepr=longrepr, when="call")

    plugin.pytest_runtest_logstart(report.nodeid, location)
    plugin.pytest_runtest_logreport(report)
    test_data = plugin.in_flight.get(report.nodeid)
    plugin.pytest_runtest_logfinish(report.nodeid, location)

    assert isinstance(test_data, TestData)
    assert isinstance(test_data.result, TestResultFailed)
    assert test_data.result.failure_reason == "the reason the test failed"
    assert test_data.result.failure_expanded == [{"expanded": [".. is quite complicated", "so here is more detail"]}]


def test_pytest_runtest_logreport_fail_exception(fake_env):
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    location = ("", None, "")
    try:
        raise Exception("a fake exception for testing")
    except Exception as e:
        longrepr = ExceptionInfo.from_exception(e)
    report = TestReport(nodeid="", location=location, keywords={}, outcome="failed", longrepr=longrepr, when="call")

    plugin.pytest_runtest_logstart(report.nodeid, location)
    plugin.pytest_runtest_logreport(report)
    test_data = plugin.in_flight.get(report.nodeid)
    plugin.pytest_runtest_logfinish(report.nodeid, location)

    assert isinstance(test_data, TestData)
    assert isinstance(test_data.result, TestResultFailed)
    assert test_data.result.failure_reason == "Exception: a fake exception for testing"

    assert isinstance(test_data.result.failure_expanded, list)
    fe = test_data.result.failure_expanded[0]
    assert list(fe.keys()) == ["expanded", "backtrace"]
    assert isinstance(fe["expanded"], list)
    assert len(fe["expanded"]) > 0
    assert isinstance(fe["backtrace"], list)
    assert len(fe["backtrace"]) > 0


def test_pytest_runtest_logreport_simple_fail(fake_env):
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    location = ("", None, "")
    report = TestReport(nodeid="", location=location, keywords={}, outcome="failed", longrepr=None, when="call")

    plugin.pytest_runtest_logstart(report.nodeid, location)
    plugin.pytest_runtest_logreport(report)

    test_data = plugin.in_flight.get(report.nodeid)
    assert test_data is not None

    assert isinstance(test_data.result, TestResultFailed)


def test_pytest_runtest_logreport_fail_exception_in_setup(fake_env):
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    location = ("", None, "")
    try:
        raise Exception("a fake fixture exception")
    except Exception as e:
        longrepr = ExceptionInfo.from_exception(e)
    report = TestReport(nodeid="", location=location, keywords={}, outcome="failed", longrepr=longrepr, when="setup")

    plugin.pytest_runtest_logstart(report.nodeid, location)
    plugin.pytest_runtest_logreport(report)
    test_data = plugin.in_flight.get(report.nodeid)
    plugin.pytest_runtest_logfinish(report.nodeid, location)

    assert isinstance(test_data, TestData)
    assert isinstance(test_data.result, TestResultFailed)
    assert test_data.result.failure_reason == "Exception: a fake fixture exception"

    assert isinstance(test_data.result.failure_expanded, list)
    fe = test_data.result.failure_expanded[0]
    assert list(fe.keys()) == ["expanded", "backtrace"]
    assert isinstance(fe["expanded"], list)
    assert len(fe["expanded"]) > 0
    assert isinstance(fe["backtrace"], list)
    assert len(fe["backtrace"]) > 0


def test_pytest_runtest_logreport_fail_exception_in_teardown(fake_env):
    """Teardown failure should override a passed call result"""
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    location = ("", None, "")

    # First, simulate a passing call phase
    call_report = TestReport(nodeid="", location=location, keywords={}, outcome="passed", longrepr=None, when="call")
    plugin.pytest_runtest_logstart(call_report.nodeid, location)
    plugin.pytest_runtest_logreport(call_report)

    # Verify it's marked as passed after call
    test_data = plugin.in_flight.get(call_report.nodeid)
    assert isinstance(test_data.result, TestResultPassed)

    # Now simulate a failing teardown phase
    try:
        raise Exception("a fake teardown exception")
    except Exception as e:
        longrepr = ExceptionInfo.from_exception(e)
    teardown_report = TestReport(nodeid="", location=location, keywords={}, outcome="failed", longrepr=longrepr, when="teardown")

    plugin.pytest_runtest_logreport(teardown_report)
    test_data = plugin.in_flight.get(teardown_report.nodeid)
    plugin.pytest_runtest_logfinish(teardown_report.nodeid, location)

    # Verify teardown failure overrides the passed result
    assert isinstance(test_data, TestData)
    assert isinstance(test_data.result, TestResultFailed)
    assert test_data.result.failure_reason == "Exception: a fake teardown exception"


def test_pytest_runtest_logreport_simple_skip(fake_env):
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    location = ("path/to/test.py", 100, "")
    longrepr = ("path/to/test.py", 123, "skippy")
    report = TestReport(nodeid="", location=location, keywords={}, outcome="skipped", longrepr=longrepr, when="call")

    plugin.pytest_runtest_logstart(report.nodeid, location)
    plugin.pytest_runtest_logreport(report)

    test_data = plugin.in_flight.get(report.nodeid)
    assert isinstance(test_data, TestData)

    assert isinstance(test_data.result, TestResultSkipped)
    # TODO: track skip reason as failure_reason via longrepr


def test_pytest_runtest_logreport_skip_in_setup(fake_env):
    """Tests skipped during setup (e.g. @pytest.mark.skip) should be recorded as skipped"""
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    location = ("path/to/test.py", 100, "")
    longrepr = ("path/to/test.py", 100, "Skipped: unconditional skip")
    report = TestReport(nodeid="", location=location, keywords={}, outcome="skipped", longrepr=longrepr, when="setup")

    plugin.pytest_runtest_logstart(report.nodeid, location)
    plugin.pytest_runtest_logreport(report)

    test_data = plugin.in_flight.get(report.nodeid)
    assert isinstance(test_data, TestData)
    assert isinstance(test_data.result, TestResultSkipped)


def test_save_json_payload_without_merge(fake_env, tmp_path, successful_test):
    payload = Payload.init(fake_env)
    payload = Payload.started(payload)
    payload = payload.push_test_data(successful_test)

    plugin = BuildkitePlugin(payload)

    path = tmp_path / "result.json"

    # Create an existing file with some data
    existing_data = [{"existing": "data"}]
    path.write_text(json.dumps(existing_data))

    # Save without merge option
    plugin.save_payload_as_json(path, merge=False)

    # Check if the data was not merged
    expected_data = [successful_test.as_json(payload.started_at)]
    assert json.loads(path.read_text()) == expected_data


def test_save_json_payload_with_merge(fake_env, tmp_path, successful_test):
    payload = Payload.init(fake_env)
    payload = Payload.started(payload)
    payload = payload.push_test_data(successful_test)

    plugin = BuildkitePlugin(payload)

    path = tmp_path / "result.json"

    # Create an existing file with some data
    existing_data = [{"existing": "data"}]
    path.write_text(json.dumps(existing_data))

    # Save with merge option
    plugin.save_payload_as_json(path, merge=True)

    # Check if the data was merged
    expected_data = existing_data + [successful_test.as_json(payload.started_at)]
    assert json.loads(path.read_text()) == expected_data


def test_save_json_payload_with_non_existent_file(fake_env, tmp_path, successful_test):
    payload = Payload.init(fake_env)
    payload = Payload.started(payload)
    payload = payload.push_test_data(successful_test)

    plugin = BuildkitePlugin(payload)

    path = tmp_path / "non_existent.json"

    # Ensure the file does not exist
    assert not path.exists()

    # Save with merge option
    plugin.save_payload_as_json(path, merge=True)

    # Check if the data was saved correctly
    expected_data = [successful_test.as_json(payload.started_at)]
    assert json.loads(path.read_text()) == expected_data


def test_save_json_payload_with_invalid_file(fake_env, tmp_path, successful_test):
    payload = Payload.init(fake_env)
    payload = Payload.started(payload)
    payload = payload.push_test_data(successful_test)

    plugin = BuildkitePlugin(payload)

    path = tmp_path / "invalid.json"

    # Create a file with invalid JSON
    path.write_text("{invalid: json}")

    # Save with merge option, expect JSONDecodeError
    with pytest.raises(json.decoder.JSONDecodeError):
        plugin.save_payload_as_json(path, merge=True)


def test_save_json_payload_with_large_data(fake_env, tmp_path, successful_test):
    payload = Payload.init(fake_env)
    payload = Payload.started(payload)
    payload = payload.push_test_data(successful_test)

    plugin = BuildkitePlugin(payload)

    path = tmp_path / "large_data.json"

    # Create an existing file with a large amount of data
    existing_data = [{"test": f"data_{i}"} for i in range(1000)]
    path.write_text(json.dumps(existing_data))

    # Save with merge option
    plugin.save_payload_as_json(path, merge=True)

    # Check if the data was merged correctly
    expected_data = existing_data + [successful_test.as_json(payload.started_at)]
    assert json.loads(path.read_text()) == expected_data


def test_save_json_payload_concurrent_merge(fake_env, tmp_path, successful_test):
    """Test that concurrent merge writes produce valid JSON with all entries.

    This exercises the race condition where multiple processes call
    save_payload_as_json(merge=True) on the same file simultaneously —
    e.g. when pants runs multiple pytest processes in parallel and each
    merges results into a shared JSON file.
    """
    import concurrent.futures

    num_writers = 10
    path = tmp_path / "concurrent.json"
    plugins = []

    for i in range(num_writers):
        payload = Payload.init(fake_env)
        payload = Payload.started(payload)
        payload = payload.push_test_data(successful_test)
        plugins.append(BuildkitePlugin(payload))

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_writers) as executor:
        futures = [
            executor.submit(plugin.save_payload_as_json, str(path), True)
            for plugin in plugins
        ]
        for f in futures:
            f.result()

    # The file must be valid JSON
    result = json.loads(path.read_text())

    # All writers must have merged their entry
    assert len(result) == num_writers


# ---------------------------------------------------------------------------
# pytest_collectreport tests
# ---------------------------------------------------------------------------

def test_pytest_collectreport_import_error(fake_env):
    """Collection errors are captured as failed tests."""
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    report = CollectReport(
        nodeid="tests/foo.py",
        outcome="failed",
        longrepr="ModuleNotFoundError: No module named 'bar'",
        result=None,
    )

    plugin.pytest_collectreport(report)

    assert plugin.payload.is_started()
    assert len(plugin.in_flight) == 0
    assert len(plugin.payload.data) == 1

    test_data = plugin.payload.data[0]
    assert test_data.name == "tests/foo.py"
    assert test_data.file_name == "tests/foo.py"
    assert test_data.scope == ""
    assert isinstance(test_data.result, TestResultFailed)
    assert "ModuleNotFoundError" in test_data.result.failure_reason
    assert test_data.tags == {"test.pytest_collection_error": "true"}
    assert test_data.is_finished()


def test_pytest_collectreport_passed_ignored(fake_env):
    """Successful collection reports are ignored."""
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    report = CollectReport(
        nodeid="tests/foo.py",
        outcome="passed",
        longrepr=None,
        result=[],
    )

    plugin.pytest_collectreport(report)

    assert not plugin.payload.is_started()
    assert len(plugin.payload.data) == 0


def test_pytest_collectreport_empty_nodeid_ignored(fake_env):
    """The root session collect report (empty nodeid) is ignored."""
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    report = CollectReport(
        nodeid="",
        outcome="failed",
        longrepr="some error",
        result=None,
    )

    plugin.pytest_collectreport(report)

    assert len(plugin.payload.data) == 0


def test_pytest_collectreport_does_not_restart_payload(fake_env):
    """If the payload is already started, pytest_collectreport does not restart it."""
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    plugin.payload = plugin.payload.started()
    original_started_at = plugin.payload.started_at

    report = CollectReport(
        nodeid="tests/foo.py",
        outcome="failed",
        longrepr="ModuleNotFoundError: No module named 'bar'",
        result=None,
    )

    plugin.pytest_collectreport(report)

    assert plugin.payload.started_at == original_started_at
    assert len(plugin.payload.data) == 1


def test_pytest_collectreport_tuple_longrepr(fake_env):
    """Tuple longrepr (path, lineno, message) is handled correctly."""
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    report = CollectReport(
        nodeid="tests/foo.py",
        outcome="failed",
        longrepr=("tests/foo.py", 8, "ModuleNotFoundError: No module named 'bar'"),
        result=None,
    )

    plugin.pytest_collectreport(report)

    assert len(plugin.payload.data) == 1
    test_data = plugin.payload.data[0]
    assert isinstance(test_data.result, TestResultFailed)
    assert "ModuleNotFoundError" in test_data.result.failure_reason


# ---------------------------------------------------------------------------
# file path normalization (rootpath -> cwd)
# ---------------------------------------------------------------------------

def test_runtest_logstart_normalizes_path_in_monorepo(fake_env, tmp_path, monkeypatch):
    """When bktec's cwd is a subdirectory of pytest's rootpath (e.g. a
    monorepo), the uploaded file_name should be relative to that cwd, not
    to pytest's rootpath, matching what Test Engine Client would discover
    from the same cwd.
    """
    rootpath = tmp_path / "monorepo"
    service_dir = rootpath / "services" / "foo"
    service_dir.mkdir(parents=True)

    monkeypatch.chdir(service_dir)

    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload, rootpath=rootpath)

    # location[0] as reported by pytest is relative to rootpath
    location = ("services/foo/test_bar.py", 10, "")
    nodeid = "services/foo/test_bar.py::test_it"

    plugin.pytest_runtest_logstart(nodeid, location)

    test_data = plugin.in_flight.get(nodeid)
    assert test_data.file_name == "test_bar.py"
    assert test_data.location == "test_bar.py:10"


def test_runtest_logstart_no_change_when_rootpath_is_cwd(fake_env, tmp_path, monkeypatch):
    """The common case: rootpath == cwd. file_name should be unchanged."""
    monkeypatch.chdir(tmp_path)

    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload, rootpath=tmp_path)

    location = ("tests/test_bar.py", 10, "")
    nodeid = "tests/test_bar.py::test_it"

    plugin.pytest_runtest_logstart(nodeid, location)

    test_data = plugin.in_flight.get(nodeid)
    assert test_data.file_name == "tests/test_bar.py"
    assert test_data.location == "tests/test_bar.py:10"


def test_runtest_logstart_no_rootpath_leaves_path_untouched(fake_env):
    """Without a rootpath (e.g. plugin constructed directly), file_name
    falls back to the raw location, preserving prior behavior."""
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    location = ("path/to/test.py", 100, "")
    nodeid = "path/to/test.py::test_it"

    plugin.pytest_runtest_logstart(nodeid, location)

    test_data = plugin.in_flight.get(nodeid)
    assert test_data.file_name == "path/to/test.py"


def test_pytest_collectreport_normalizes_path_in_monorepo(fake_env, tmp_path, monkeypatch):
    """Collection errors (pytest_collectreport) should also normalize
    file_name relative to cwd, consistent with pytest_runtest_logstart."""
    rootpath = tmp_path / "monorepo"
    service_dir = rootpath / "services" / "foo"
    service_dir.mkdir(parents=True)

    monkeypatch.chdir(service_dir)

    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload, rootpath=rootpath)

    report = CollectReport(
        nodeid="services/foo/test_bar.py",
        outcome="failed",
        longrepr="ModuleNotFoundError: No module named 'bar'",
        result=None,
    )

    plugin.pytest_collectreport(report)

    test_data = plugin.payload.data[0]
    assert test_data.file_name == "test_bar.py"


def test_pytest_collectreport_deduplicates(fake_env):
    """Repeated collection errors for the same nodeid produce only one entry.

    With xdist, each worker fires pytest_collectreport independently for the
    same file.  Without dedup, the same error would appear N times in the
    payload (once per worker).
    """
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    report = CollectReport(
        nodeid="tests/foo.py",
        outcome="failed",
        longrepr="ModuleNotFoundError: No module named 'bar'",
        result=None,
    )

    plugin.pytest_collectreport(report)
    plugin.pytest_collectreport(report)
    plugin.pytest_collectreport(report)

    assert len(plugin.payload.data) == 1


# ---------------------------------------------------------------------------
# fork-per-test runners (e.g. pytest-forked)
# ---------------------------------------------------------------------------

def test_finalize_test_skipped_in_forked_child(fake_env):
    """A fork-per-test child holds a discarded copy of the plugin state, so
    finalizing there must be a no-op — it would otherwise emit a spurious
    'no result set at finalization' warning for every test, because the
    child runs the test protocol with log=False (no logreport in-child).
    The owning process finalizes from the replayed reports instead.
    """
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    location = ("", None, "")
    nodeid = "test_sample.py::test_happy"
    plugin.pytest_runtest_logstart(nodeid, location)

    # Simulate running in a forked child: the current pid no longer matches
    # the pid recorded when the plugin was constructed.
    plugin._owner_pid = os.getpid() + 1

    assert plugin.finalize_test(nodeid) is False
    assert nodeid in plugin.in_flight
    assert len(plugin.payload.data) == 0


def test_finalize_test_runs_in_owning_process(fake_env):
    """In the owning process finalize_test behaves as before."""
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    location = ("", None, "")
    report = TestReport(nodeid="test_sample.py::test_happy", location=location, keywords={}, outcome="passed", longrepr=None, when="call")

    plugin.pytest_runtest_logstart(report.nodeid, location)
    plugin.pytest_runtest_logreport(report)

    assert plugin.finalize_test(report.nodeid) is True
    assert report.nodeid not in plugin.in_flight
    assert len(plugin.payload.data) == 1
    assert isinstance(plugin.payload.data[0].result, TestResultPassed)


def test_execution_tags_captured_at_collection_and_applied_at_finalize(fake_env):
    """execution_tag markers are captured during collection (which happens in
    the owning process) and applied at finalization, so they survive
    fork-per-test runners where pytest_runtest_makereport only fires in the
    discarded child process.
    """
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    nodeid = "test_sample.py::test_tagged"
    marker = SimpleNamespace(args=("team", "backend"))
    bad_marker = SimpleNamespace(args=("only-one-arg",))
    item = SimpleNamespace(nodeid=nodeid, iter_markers=lambda name: [marker, bad_marker])
    untagged_item = SimpleNamespace(nodeid="test_sample.py::test_plain", iter_markers=lambda name: [])
    config = SimpleNamespace(getoption=lambda name: None)

    plugin.pytest_collection_modifyitems(config, [item, untagged_item])

    assert plugin._tags_by_nodeid == {nodeid: (("team", "backend"),)}

    location = ("", None, "")
    report = TestReport(nodeid=nodeid, location=location, keywords={}, outcome="passed", longrepr=None, when="call")
    plugin.pytest_runtest_logstart(nodeid, location)
    plugin.pytest_runtest_logreport(report)
    plugin.pytest_runtest_logfinish(nodeid, location)

    assert len(plugin.payload.data) == 1
    assert plugin.payload.data[0].tags == {"team": "backend"}
