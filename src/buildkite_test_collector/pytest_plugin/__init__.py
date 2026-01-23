"""Buildkite test collector for Pytest."""

import os
import pytest

from ..collector.payload import Payload
from ..collector.run_env import RunEnvBuilder
from ..collector.api import API
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
    env = RunEnvBuilder(os.environ).build()

    config.addinivalue_line("markers",
        "execution_tag(key, value): "
        "add tag to test execution for Buildkite Test Collector. "
        "Both key and value must be a string.")

    plugin = BuildkitePlugin(Payload.init(env))
    setattr(config, '_buildkite', plugin)
    config.pluginmanager.register(plugin)


@pytest.hookimpl
def pytest_unconfigure(config):
    """pytest_unconfigure hook callback"""
    plugin = getattr(config, '_buildkite', None)

    if plugin:
        api = API(os.environ)
        xdist_plugin = config.pluginmanager.getplugin("xdist")
        if xdist_plugin is not None:
            numprocesses = config.getoption("numprocesses")
        else:
            numprocesses = None
        xdist_enabled = (
            xdist_plugin is not None
            and numprocesses is not None
            and numprocesses > 0
        )
        is_xdist_worker = hasattr(config, 'workerinput')

        is_controller = not xdist_enabled or (xdist_enabled and not is_xdist_worker)

        # When xdist is not installed, or when it's installed and not enabled
        if not xdist_enabled:
            list(api.submit(plugin.payload))

        # When xdist is activated, we want to submit from worker thread only, because they have
        # access to tag data
        if xdist_enabled and is_xdist_worker:
            list(api.submit(plugin.payload))

        # We only want a single thread to write to the json file.
        # When xdist is enabled, that will be the controller thread.
        if is_controller:
            # Note that when xdist is used, this JSON output file will NOT contain tags.
            jsonpath = config.option.jsonpath
            if jsonpath:
                plugin.save_payload_as_json(jsonpath, merge=config.option.mergejson)

        del config._buildkite
        config.pluginmanager.unregister(plugin)

def pytest_addoption(parser):
    """add custom option to pytest"""
    group = parser.getgroup('buildkite', 'Buildkite Test Collector')
    group.addoption(
        '--json',
        default=None,
        action='store',
        dest="jsonpath",
        metavar="path",
        help='save json file at given path'
    )
    group.addoption(
        '--merge-json',
        default=False,
        action='store_true',
        dest="mergejson",
        help='merge json output with existing file, if it exists'
    )
