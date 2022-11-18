from uuid import uuid4

import os
import mock
import responses

from buildkite_test_collector.collector.run_env import detect_env
from buildkite_test_collector.collector.api import submit
from buildkite_test_collector.collector.payload import Payload


def test_submit_with_missing_api_key_environment_variable_returns_none():
    with mock.patch.dict(os.environ, {"CI": "true", "BUILDKITE_ANALYTICS_TOKEN": ""}):
        payload = Payload.init(detect_env())

        assert submit(payload) is None


def test_submit_with_invalid_api_key_environment_variable_returns_none():
    with mock.patch.dict(os.environ, {"CI": "true", "BUILDKITE_ANALYTICS_TOKEN": "\n"}):
        payload = Payload.init(detect_env())

        assert submit(payload) is None


@responses.activate
def test_submit_with_payload_returns_an_api_response(successful_test):
    responses.add(
        responses.POST,
        "https://analytics-api.buildkite.com/v1/uploads",
        json={'id': str(uuid4()),
              'run_id': str(uuid4()),
              'queued': 1,
              'skipped': 0,
              'errors': [],
              'run_url': 'https://buildkite.com/organizations/alembic/analytics/suites/test/runs/52c5d9f6-a4f2-4a2d-a1e6-993335789c92'},
        status=202)

    with mock.patch.dict(os.environ, {"CI": "true", "BUILDKITE_ANALYTICS_TOKEN": str(uuid4())}):
        payload = Payload.init(detect_env())
        payload = Payload.started(payload)

        payload = payload.push_test_data(successful_test)

        result = submit(payload)

        assert result.status_code >= 200
        assert result.status_code < 300

        json = result.json()
        assert len(json["errors"]) == 0
        assert json['queued'] == 1


@responses.activate
def test_submit_with_large_payload_batches_requests(successful_test, failed_test):
    responses.add(
        responses.POST,
        "https://analytics-api.buildkite.com/v1/uploads",
        json={'id': str(uuid4()),
              'run_id': str(uuid4()),
              'queued': 1,
              'skipped': 0,
              'errors': [],
              'run_url': 'https://buildkite.com/organizations/alembic/analytics/suites/test/runs/52c5d9f6-a4f2-4a2d-a1e6-993335789c92'},
        status=202)
    responses.add(
        responses.POST,
        "https://analytics-api.buildkite.com/v1/uploads",
        json={'id': str(uuid4()),
              'run_id': str(uuid4()),
              'queued': 1,
              'skipped': 0,
              'errors': [],
              'run_url': 'https://buildkite.com/organizations/alembic/analytics/suites/test/runs/52c5d9f6-a4f2-4a2d-a1e6-993335789c92'},
        status=202)

    with mock.patch.dict(os.environ, {"CI": "true", "BUILDKITE_ANALYTICS_TOKEN": str(uuid4())}):
        payload = Payload.init(detect_env())
        payload = Payload.started(payload)

        payload = payload.push_test_data(successful_test)
        payload = payload.push_test_data(failed_test)

        result = submit(payload, batch_size=1)

        assert result.status_code >= 200
        assert result.status_code < 300

        json = result.json()
        assert len(json["errors"]) == 0
        assert json['queued'] == 1
