import json
import pytest

from buildkite_test_collector.collector.payload import Payload, TestData, TestResultFailed, TestResultPassed, TestResultSkipped
from buildkite_test_collector.pytest_plugin import BuildkitePlugin

from _pytest._code.code import ExceptionInfo
from _pytest.reports import TestReport

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
