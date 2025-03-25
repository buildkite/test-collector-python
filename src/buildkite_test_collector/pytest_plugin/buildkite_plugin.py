"""Buildkite test collector plugin for Pytest"""
import json

from uuid import uuid4

from ..collector.payload import TestData

class BuildkitePlugin:
    """Buildkite test collector plugin for Pytest"""

    def __init__(self, payload):
        self.payload = payload
        self.in_flight = {}
        self.spans = {}

    def pytest_runtest_logstart(self, nodeid, location):
        """pytest_runtest_logstart hook callback"""
        if not self.payload.is_started():
            self.payload = self.payload.started()

        chunks = nodeid.split("::")

        test_data = TestData.start(
            uuid4(),
            scope="::".join(chunks[:-1]),
            name=chunks[-1],
            file_name=location[0],
            location=f"{location[0]}:{location[1]}"
        )
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

    def save_payload_as_json(self, path):
        """ Save payload into a json file """
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.payload.as_json(), f)
