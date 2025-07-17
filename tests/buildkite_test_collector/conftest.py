
from dataclasses import replace
from datetime import timedelta
from random import randint
from uuid import uuid4

import pytest

from buildkite_test_collector.collector.payload import TestData, TestResultPassed, TestHistory, Payload, TestResultFailed, TestResultSkipped
from buildkite_test_collector.collector.run_env import RunEnv
from buildkite_test_collector.collector.instant import Instant


@pytest.fixture
def successful_test(history_finished) -> TestData:
    return TestData(
        id=uuid4(),
        scope="wyld stallyns",
        name="san dimas meltdown",
        location="san_dimas_meltdown.py:1",
        file_name="san_dimas_meltdown.py",
        result=TestResultPassed(),
        history=history_finished
    )


@pytest.fixture
def failed_test(successful_test) -> TestData:
    return replace(successful_test, result=TestResultFailed("bogus"))


@pytest.fixture
def skipped_test(successful_test) -> TestData:
    return replace(successful_test, result=TestResultSkipped())


@pytest.fixture
def incomplete_test(history_started) -> TestData:
    return TestData(
        id=uuid4(),
        scope="wyld stallyns",
        name="san dimas meltdown",
        location="san_dimas_meltdown.py:1",
        file_name="san_dimas_meltdown.py",
        result=None,
        history=history_started
    )


@pytest.fixture
def history_started() -> TestHistory:
    return TestHistory(
        start_at=Instant.now(),
        end_at=None,
        duration=None,
        children=()
    )


@pytest.fixture
def history_finished() -> TestHistory:
    start_at = Instant.now()
    duration = timedelta(minutes=2, seconds=18)
    end_at = start_at + duration

    return TestHistory(
        start_at=start_at,
        end_at=end_at,
        duration=duration,
        children=()
    )


@pytest.fixture
def fake_env() -> RunEnv:
    return RunEnv(
        ci="example",
        key=str(uuid4()),
        number=str(randint(0, 1000)),
        job_id=str(randint(0, 1000)),
        branch="rufus",
        commit_sha=uuid4().hex,
        message="Be excellent to each other",
        url="https://example.test/buildkite")


@pytest.fixture
def payload(fake_env) -> Payload:
    return Payload.started(Payload.init(fake_env))
