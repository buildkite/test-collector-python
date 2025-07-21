"""Buildkite test collector plugin for Pytest"""
import json
import os
from uuid import uuid4

from filelock import FileLock

from ..collector.payload import TestData
from .logger import logger
from .failure_reasons import failure_reasons

class BuildkitePlugin:
    """Buildkite test collector plugin for Pytest"""

    def __init__(self, payload):
        self.payload = payload
        self.in_flight = {}
        self.spans = {}

    def pytest_runtest_logstart(self, nodeid, location):
        """pytest_runtest_logstart hook callback"""
        logger.debug('hook=pytest_runtest_logstart nodeid=%s', nodeid)

        if self.payload.is_started():
            logger.debug('-> already started_at=%s(monotonic)', self.payload.started_at)
        else:
            self.payload = self.payload.started()
            logger.debug('-> started_at=%s(monotonic)', self.payload.started_at)

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
        logger.debug('hook=pytest_runtest_logreport nodeid=%s when=%s', report.nodeid, report.when)

        # This hook is called three times during the lifecycle of a test:
        # after the setup phase, the call phase, and the teardown phase.
        # We capture outcomes from the call phase, or setup phase if it failed
        # (since setup failures prevent the call phase from running).
        # See: https://github.com/buildkite/test-collector-python/pull/45
        if report.when == 'call' or (report.when == 'setup' and report.failed):
            self.update_test_result(report)

    # This hook only runs in xdist worker thread, not controller thread.
    # We used to rely on pytest_runtest_teardown, but somehow xdist will ignore it
    # in both controller and worker thread.
    def pytest_runtest_makereport(self, item, call):
        """pytest_runtest_hook hook callback to mark test as finished and add it to the payload"""
        logger.debug('hook=pytest_runtest_makereport nodeid=%s when=%s', item.nodeid, call.when)

        if call.when != 'teardown':
            return

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
        logger.debug('hook=pytest_runtest_logfinish nodeid=%s', nodeid)

        if self.finalize_test(nodeid):
            # This is expected to happen in xdist controller thread.
            # Where it would skip many pytest_runtest_xxx hooks
            logger.debug(
                'Detected possible interference in pytest_runtest_makereport hook (xdist?). '
                'Falling back to pytest_runtest_logfinish'
            )

    def update_test_result(self, report):
        """Update test result based on pytest report"""
        test_data = self.in_flight.get(report.nodeid)

        if test_data:
            if report.passed:
                logger.debug('-> test passed')
                test_data = test_data.passed()

            if report.failed:
                failure_reason, failure_expanded = failure_reasons(longrepr=report.longrepr)
                logger.debug('-> test failed: %s', failure_reason)
                test_data = test_data.failed(
                    failure_reason=failure_reason,
                    failure_expanded=failure_expanded
                )

            if report.skipped:
                logger.debug('-> test skipped')
                test_data = test_data.skipped()

            # TestData is immutable.
            # We need to replace the test_data in `in_flight` with updated test_data,
            # so we can get the correct result when we process it during the teardown hook.
            self.in_flight[report.nodeid] = test_data


    def finalize_test(self, nodeid):
        """ Attempting to move test data for a nodeid to payload area for upload """
        logger.debug('-> finalize_test nodeid=%s', nodeid)
        test_data = self.in_flight.get(nodeid)
        if not test_data:
            logger.debug('-> finalize_test: not in flight: %s', nodeid)
            return False
        del self.in_flight[nodeid]
        test_data = test_data.finish()
        logger.debug('-> finalize_test nodeid=%s duration=%s', nodeid, test_data.history.duration)
        self.payload = self.payload.push_test_data(test_data)
        return True

    def save_payload_as_json(self, path, merge=False):
        """Save payload into a json file, merging with existing data if merge is True"""
        data = list(self.payload.as_json()["data"])

        if merge:
            lock = FileLock(f"{path}.lock")
            with lock:
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                    # Merge existing data with current payload
                    data = existing_data + data

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
