import pytest

from buildkite_test_collector.pytest_plugin.buildkite_plugin import BuildkitePlugin
from buildkite_test_collector.pytest_plugin.span_collector import SpanCollector


@pytest.fixture
def plugin(payload):
    return BuildkitePlugin(payload)


@pytest.fixture
def span_collector(plugin, successful_test):
    plugin.in_flight[successful_test.id] = successful_test
    return SpanCollector(nodeid=successful_test.id, plugin=plugin)
