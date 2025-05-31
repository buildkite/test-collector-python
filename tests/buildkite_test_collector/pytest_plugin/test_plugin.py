import json

from buildkite_test_collector.collector.payload import Payload
from buildkite_test_collector.pytest_plugin import BuildkitePlugin


def test_runtest_logstart_with_unstarted_payload(fake_env):
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    assert plugin.payload.started_at is None

    plugin.pytest_runtest_logstart("wat::when", [1, 2])

    assert plugin.payload.started_at is not None


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


def test_save_json_payload_with_empty_file(fake_env, tmp_path, successful_test):
    payload = Payload.init(fake_env)
    payload = Payload.started(payload)
    payload = payload.push_test_data(successful_test)

    plugin = BuildkitePlugin(payload)

    path = tmp_path / "empty.json"

    # Create an empty file
    path.write_text("")

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

    # Save with merge option
    plugin.save_payload_as_json(path, merge=True)

    # Check if the data was saved correctly
    expected_data = [successful_test.as_json(payload.started_at)]
    assert json.loads(path.read_text()) == expected_data


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
