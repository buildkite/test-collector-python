from buildkite_test_collector.pytest_plugin import BuildkitePlugin
from buildkite_test_collector.collector.payload import Payload
from pathlib import Path

import json

def test_runtest_logstart_with_unstarted_payload(fake_env):
    payload = Payload.init(fake_env)
    plugin = BuildkitePlugin(payload)

    assert plugin.payload.started_at is None

    plugin.pytest_runtest_logstart("wat::when", [1, 2])

    assert plugin.payload.started_at is not None


def test_save_json_payload(fake_env, tmp_path, successful_test):
    payload = Payload.init(fake_env)
    payload = Payload.started(payload)
    payload = payload.push_test_data(successful_test)

    plugin = BuildkitePlugin(payload)

    path = tmp_path / "result.json"
    plugin.save_payload_as_json(path)

    assert path.read_text() == json.dumps([successful_test.as_json(payload.started_at)])
