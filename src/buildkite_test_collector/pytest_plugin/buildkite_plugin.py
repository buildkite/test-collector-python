"""Buildkite test collector plugin for Pytest"""
import json
from uuid import uuid4

from ..collector.payload import TestData
from .logger import logger

class BuildkitePlugin:
    """Buildkite test collector plugin for Pytest"""

    def __init__(self, payload):
        self.payload = payload
        self.in_flight = {}
        self.spans = {}

    def pytest_runtest_logstart(self, nodeid, location):
        """pytest_runtest_logstart hook callback"""
        logger.debug('Enter pytest_runtest_logstart for %s', nodeid)
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
        """pytest_runtest_logreport hook callback to get test outcome after test call"""

        # This hook is called three times during the lifecycle of a test:
        # after the setup phase, the call phase, and the teardown phase.
        # Since we want to capture the outcome from the call phase,
        # we only proceed when this hook is triggered following the call phase.
        # See: https://github.com/buildkite/test-collector-python/pull/45
        if report.when != 'call':
            return

        nodeid = report.nodeid
        test_data = self.in_flight.get(nodeid)
        logger.debug('Enter pytest_runtest_logreport for %s', nodeid)

        if test_data:
            if report.passed:
                test_data = test_data.passed()

            if report.failed:
                test_data = test_data.failed(report.longreprtext)

            if report.skipped:
                test_data = test_data.skipped()

            # TestData is immutable.
            # We need to replace the test_data in `in_flight` with updated test_data,
            # so we can get the correct result when we process it during the teardown hook.
            self.in_flight[nodeid] = test_data

    # This hook only runs in xdist worker thread, not controller thread.
    # We used to rely on pytest_runtest_teardown, but somehow xdist will ignore it
    # in both controller and worker thread.
    def pytest_runtest_makereport(self, item, call):
        """pytest_runtest_hook hook callback to mark test as finished and add it to the payload"""

        if call.when != 'teardown':
            return

        logger.debug('Enter pytest_runtest_makereport for %s', item.nodeid)
        test_data = self.in_flight.get(item.nodeid)

        if test_data:
            tags = item.iter_markers("execution_tag")
            for tag in tags:
                test_data = test_data.tag_execution(tag.args[0], tag.args[1])

            self.in_flight[item.nodeid] = test_data

            self.finalize_test(item.nodeid)
        else:
            logger.warning('Unexpected missing test_data during pytest_runtest_makereport')

    # If pytest_runtest_makereport runs properly then this hook is unnecessary.
    # But as we commented above, in some cases, in pytest-xdist controller thread,
    # pytest_runtest_makereport will be skipped.
    # In that case, it's necessary for this hook to work as a fallback mechanism.
    def pytest_runtest_logfinish(self, nodeid, location):  # pylint: disable=unused-argument
        """pytest_runtest_logfinish hook always runs in the very end"""
        logger.debug('Enter pytest_runtest_logfinish for %s', nodeid)
        if self.finalize_test(nodeid):
            # This is expected to happen in xdist controller thread.
            # Where it would skip many pytest_runtest_xxx hooks
            logger.debug(
                'Detected possible interference in pytest_runtest_makereport hook (xdist?). '
                'Falling back to pytest_runtest_logfinish'
            )

    def finalize_test(self, nodeid):
        """ Attempting to move test data for a nodeid to payload area for upload """
        test_data = self.in_flight.get(nodeid)
        if test_data:
            del self.in_flight[nodeid]
            test_data = test_data.finish()
            self.payload = self.payload.push_test_data(test_data)
            return True
        return False

    def save_payload_as_json(self, path):
        """ Save payload into a json file """
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.payload.as_json()["data"], f)
