"""Buildkite test collector for Pytest."""

from logging import warning
from uuid import uuid4

import pytest

from .collector.payload import Payload, TestData
from .collector.run_env import detect_env
from .collector.api import submit


class BuildkitePlugin:
    """Buildkite test collector plugin for Pytest"""

    def __init__(self, payload):
        self.payload = payload
        self.in_flight = {}

    def pytest_runtestloop(self, session):
        """pytest_runtestloop hook callback"""
        _pylint_ignore = session
        self.payload = self.payload.started()

    def pytest_runtest_logstart(self, nodeid, location):
        """pytest_runtest_logstart hook callback"""
        chunks = nodeid.split("::")
        scope = "::".join(chunks[:-1])
        name = chunks[-1]
        location = f"{location[0]}:{location[1]}"

        test_data = TestData.start(uuid4(), scope, name, nodeid, location)
        self.in_flight[nodeid] = test_data

    def pytest_runtest_logreport(self, report):
        """pytest_runtest_logreport hook callback"""
        if report.when != 'call':
            return

        nodeid = report.nodeid
        test_data = self.in_flight.get(nodeid)

        if test_data:
            test_data = test_data.finish()

            if report.passed:
                test_data = test_data.passed()

            if report.failed:
                test_data = test_data.failed(report.longreprtext)

            if report.skipped:
                test_data = test_data.skipped()

            del self.in_flight[nodeid]
            self.payload = self.payload.push_test_data(test_data)


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    """pytest_configure hook callback"""
    env = detect_env()

    if env:
        plugin = BuildkitePlugin(Payload.init(env))
        setattr(config, '_buildkite', plugin)
        config.pluginmanager.register(plugin)
    else:
        warning("Unable to detect CI environment.  No test analytics will be sent.")


def pytest_unconfigure(config):
    """pytest_unconfigure hook callback"""
    plugin = getattr(config, '_buildkite', None)
    if plugin:
        submit(plugin.payload)
        del config._buildkite
        config.pluginmanager.unregister(plugin)
