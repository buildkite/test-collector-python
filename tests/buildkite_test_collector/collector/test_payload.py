from datetime import timedelta
from functools import reduce

import pytest

from buildkite_test_collector.collector.payload import Payload, TestHistory, TestData, TestResultFailed, TestResultPassed, TestResultSkipped, TestSpan
from buildkite_test_collector.collector.instant import Instant


def test_payload_init_has_empty_data(fake_env):
    payload = Payload.init(fake_env)
    assert len(payload.data) == 0


def test_payload_init_has_no_started_at(fake_env):
    payload = Payload.init(fake_env)
    assert payload.started_at is None


def test_payload_started_sets_started_at_time(fake_env):
    payload = Payload.init(fake_env)
    payload = Payload.started(payload)
    assert payload.started_at is not None


def test_payload_into_batches_works_as_advertised(payload, successful_test):
    payload = reduce(lambda p, _: p.push_test_data(
        successful_test), range(100), payload)

    payloads = payload.into_batches(33)

    assert len(payloads) == 4

    assert len(payloads[0].data) == 33
    assert len(payloads[1].data) == 33
    assert len(payloads[2].data) == 33
    assert len(payloads[3].data) == 1


def test_payload_push_test_data(payload, successful_test):
    new_payload = payload.push_test_data(successful_test)

    assert len(payload.data) == 0
    assert len(new_payload.data) == 1
    assert payload.run_env == new_payload.run_env
    assert payload.started_at == new_payload.started_at


def test_payload_as_json(payload, successful_test):
    payload = payload.push_test_data(successful_test)

    json = payload.as_json()

    assert json["format"] == "json"
    assert json["run_env"]["key"] == payload.run_env.key
    assert json["data"][0]["id"] == str(successful_test.id)


def test_test_history_with_no_end_at_is_not_finished():
    hist = TestHistory(
        start_at=Instant.now(),
        end_at=None,
        duration=None)

    assert hist.is_finished() is not True


def test_test_history_with_end_at_is_finished():
    start_at = Instant.now()
    duration = timedelta(minutes=2, seconds=18)
    end_at = start_at + duration

    hist = TestHistory(
        start_at=start_at,
        end_at=end_at,
        duration=duration)

    assert hist.is_finished() is True


def test_test_history_as_json():
    now = Instant.now()
    start_at = now + timedelta(minutes=1)
    duration = timedelta(minutes=2, seconds=18)
    end_at = start_at + duration

    hist = TestHistory(
        start_at=start_at,
        end_at=end_at,
        duration=duration)

    json = hist.as_json(now)

    assert json["section"] == "top"
    assert json["start_at"] == 60
    assert json["end_at"] == 198
    assert json["duration"] == 138
    assert len(json["children"]) == 0


def test_test_data_start(successful_test):
    test_data = TestData.start(id=successful_test.id,
                               scope=successful_test.scope,
                               name=successful_test.name,
                               location=successful_test.location)

    assert test_data.history.start_at.seconds == pytest.approx(
        Instant.now().seconds, 1.0)


def test_test_data_finish_when_already_finished_is_a_noop(successful_test):
    assert successful_test == successful_test.finish()


def test_test_data_finish(incomplete_test):
    test_data = incomplete_test.finish()

    assert test_data.history.end_at.seconds == pytest.approx(
        Instant.now().seconds, 1.0)
    assert test_data.history.duration.total_seconds() == pytest.approx(0, abs=0.5)


def test_test_data_passed(incomplete_test):
    test_data = incomplete_test.passed()

    assert isinstance(test_data.result, TestResultPassed)


def test_test_data_failed(incomplete_test):
    test_data = incomplete_test.failed("bogus")

    assert isinstance(test_data.result, TestResultFailed)
    assert test_data.result.failure_reason == "bogus"


def test_test_data_skipped(incomplete_test):
    test_data = incomplete_test.skipped()

    assert isinstance(test_data.result, TestResultSkipped)


def test_test_data_as_json(incomplete_test):
    now = Instant.now()
    json = incomplete_test.as_json(now)

    assert json["id"] == str(incomplete_test.id)
    assert json["scope"] == incomplete_test.scope
    assert json["name"] == incomplete_test.name
    assert json["location"] == incomplete_test.location
    assert json["file_name"] == incomplete_test.file_name
    assert json["history"] == incomplete_test.history.as_json(now)


def test_test_data_as_json_when_passed(successful_test):
    json = successful_test.as_json(Instant.now())

    assert json["result"] == "passed"


def test_test_data_as_json_when_failed(failed_test):
    json = failed_test.as_json(Instant.now())

    assert json["result"] == "failed"
    assert json["failure_reason"] == "bogus"
    assert json["failure_expanded"] == [{'expanded': ['test failed'], 'backtrace': ['test.py:1']}]


def test_test_data_as_json_when_skipped(skipped_test):
    json = skipped_test.as_json(Instant.now())

    assert json["result"] == "skipped"

class TestTestDataTagExecution:
    def test_test_data_tag_execution(self, successful_test):
        test_data = successful_test.tag_execution("owner", "test-engine")
        test_data = test_data.tag_execution("python.version", "3.12.3")

        expected_tags = {"owner": "test-engine", "python.version": "3.12.3"}

        assert test_data.tags == expected_tags

        json = test_data.as_json(Instant.now())
        assert json["tags"] == {"owner": "test-engine", "python.version": "3.12.3"}

    def test_test_data_tag_execution_non_string(self, successful_test):
        with pytest.raises(TypeError):
            successful_test.tag_execution("feature", True)

        with pytest.raises(TypeError):
            successful_test.tag_execution(777, "lucky")


class TestSpanValidation:
    """Tests for TestSpan detail validation"""

    def test_sql_span_with_valid_detail(self):
        """SQL span with correct detail structure should succeed"""
        span = TestSpan(
            section='sql',
            duration=timedelta(seconds=1),
            detail={'query': 'SELECT * FROM users'}
        )
        assert span.detail == {'query': 'SELECT * FROM users'}

    def test_sql_span_without_query_field_fails(self):
        """SQL span without 'query' field should raise ValueError"""
        with pytest.raises(ValueError, match="SQL span detail must contain 'query' field"):
            TestSpan(
                section='sql',
                duration=timedelta(seconds=1),
                detail={'wrong_field': 'SELECT * FROM users'}
            )

    def test_annotation_span_with_valid_detail(self):
        """Annotation span with correct detail structure should succeed"""
        span = TestSpan(
            section='annotation',
            duration=timedelta(seconds=1),
            detail={'content': 'Test annotation'}
        )
        assert span.detail == {'content': 'Test annotation'}

    def test_annotation_span_without_content_field_fails(self):
        """Annotation span without 'content' field should raise ValueError"""
        with pytest.raises(ValueError, match="Annotation span detail must contain 'content' field"):
            TestSpan(
                section='annotation',
                duration=timedelta(seconds=1),
                detail={'wrong_field': 'Test annotation'}
            )

    def test_http_span_with_valid_detail(self):
        """HTTP span with all required fields should succeed"""
        span = TestSpan(
            section='http',
            duration=timedelta(seconds=1),
            detail={'method': 'GET', 'url': 'https://example.com', 'lib': 'requests'}
        )
        assert span.detail == {'method': 'GET', 'url': 'https://example.com', 'lib': 'requests'}

    def test_http_span_missing_method_fails(self):
        """HTTP span missing 'method' field should raise ValueError"""
        with pytest.raises(ValueError, match="HTTP span detail missing required fields"):
            TestSpan(
                section='http',
                duration=timedelta(seconds=1),
                detail={'url': 'https://example.com', 'lib': 'requests'}
            )

    def test_http_span_missing_multiple_fields_fails(self):
        """HTTP span missing multiple fields should raise ValueError"""
        with pytest.raises(ValueError, match="HTTP span detail missing required fields"):
            TestSpan(
                section='http',
                duration=timedelta(seconds=1),
                detail={'method': 'GET'}
            )

    def test_sleep_span_without_detail(self):
        """Sleep span without detail should succeed"""
        span = TestSpan(
            section='sleep',
            duration=timedelta(seconds=1)
        )
        assert span.detail is None

    def test_sleep_span_with_detail_is_allowed(self):
        """Sleep span with detail (though not required) should be allowed"""
        span = TestSpan(
            section='sleep',
            duration=timedelta(seconds=1),
            detail={'reason': 'rate limiting'}
        )
        assert span.detail == {'reason': 'rate limiting'}

    def test_span_with_none_detail(self):
        """Span with None detail should succeed"""
        span = TestSpan(
            section='sql',
            duration=timedelta(seconds=1),
            detail=None
        )
        assert span.detail is None

    def test_span_with_string_detail_fails(self):
        """Span with string instead of dict should raise TypeError"""
        with pytest.raises(TypeError, match="detail must be a dict, got str"):
            TestSpan(
                section='sql',
                duration=timedelta(seconds=1),
                detail='SELECT * FROM users'
            )
