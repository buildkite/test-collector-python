"""Buildkite test collector for Pytest."""

from logging import warning
from os import environ

import pytest

from ..collector.payload import Payload
from ..collector.run_env import detect_env
from ..collector.api import submit
from .span_collector import SpanCollector
from .buildkite_plugin import BuildkitePlugin


@pytest.fixture
def spans(request):
    """A pytest fixture which returns an instance of SpanCollector"""
    nodeid = request.node.nodeid
    plugin = getattr(request.config, '_buildkite', None)

    return SpanCollector(plugin=plugin, nodeid=nodeid)


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    """pytest_configure hook callback"""
    env = detect_env()
    debug = environ.get("BUILDKITE_ANALYTICS_DEBUG_ENABLED")

    if env:
        plugin = BuildkitePlugin(Payload.init(env))
        setattr(config, '_buildkite', plugin)
        config.pluginmanager.register(plugin)
    elif debug:
        warning("Unable to detect CI environment.  No test analytics will be sent.")


@pytest.hookimpl
def pytest_unconfigure(config):
    """pytest_unconfigure hook callback"""
    plugin = getattr(config, '_buildkite', None)
    if plugin and not hasattr(config, "workerinput"):
        submit(plugin.payload)
        del config._buildkite
        config.pluginmanager.unregister(plugin)
