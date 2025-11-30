import time
from datetime import timedelta

from buildkite_test_collector.collector.payload import TestSpan


def test_record_adds_span_to_plugin(span_collector):
    span_collector.record(TestSpan(
        section='http',
        duration=timedelta(seconds=3),
        detail={'method': 'GET', 'url': 'https://example.com', 'lib': 'requests'}))

    assert len(span_collector.current_test().history.children) == 1


def test_measure_adds_span_to_plugin(span_collector):
    with span_collector.measure('annotation', {'content': 'test annotation'}):
        time.sleep(0.001)

    assert len(span_collector.current_test().history.children) == 1
