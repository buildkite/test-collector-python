"""An fixture object which can add tracing spans to test analytics"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Literal, Optional, Any

from ..collector.payload import TestSpan, TestData
from ..collector.instant import Instant
from .buildkite_plugin import BuildkitePlugin


@dataclass
class SpanCollector:
    """
    Adds spans to the currently running test.

    The SpanCollector object is returned by the `spans` fixture.  You can use it
    to manually instrument elements of your tests (such as HTTP requests or SQL
    queries).
    """

    nodeid: str
    plugin: BuildkitePlugin = None

    def record(self, span: TestSpan) -> None:
        """
        Add a span to the current test.
        """
        if self.plugin is not None:
            test_data = self.plugin.in_flight[self.nodeid].push_span(span)
            self.plugin.in_flight[self.nodeid] = test_data

    @contextmanager
    def measure(self, section: Literal['http', 'sql', 'sleep', 'annotation'],
                detail: Optional[dict] = None) -> Any:
        """
        Measure the execution time of some code and record it as a span.

        The detail parameter should be a dict matching the expected format for each section type:
        - sql: {"query": str}
        - annotation: {"content": str}
        - http: {"method": str, "url": str, "lib": str}
        - sleep: no detail required

        Example:

        .. code-block:: python

            def test_measure_http_request(spans):
                detail = {'method': 'GET', 'url': 'https://api.github.com/zen', 'lib': 'requests'}
                with spans.measure('http', detail):
                    requests.get("https://api.github.com/zen")

            def test_measure_sql_query(spans):
                with spans.measure('sql', {'query': 'SELECT * FROM users'}):
                    db.execute('SELECT * FROM users')
        """
        start_at = Instant.now()
        try:
            yield

        finally:
            end_at = Instant.now()

            self.record(TestSpan(section=section, detail=detail,
                        start_at=start_at, end_at=end_at, duration=end_at - start_at))

    def current_test(self) -> TestData:
        """Returns the `TestData` of the currently executing test"""
        return self.plugin.in_flight[self.nodeid]
