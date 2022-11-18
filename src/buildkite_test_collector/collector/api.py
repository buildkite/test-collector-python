"""Buildkite Test Analytics API"""

from typing import Optional
from os import environ
from sys import stderr
from requests import post, Response
from requests.exceptions import InvalidHeader
from .payload import Payload


def submit(payload: Payload, batch_size=100) -> Optional[Response]:
    """Submit a payload to the API"""
    token = environ.get("BUILDKITE_ANALYTICS_TOKEN")
    debug = environ.get("BUILDKITE_ANALYTICS_DEBUG_ENABLED")
    response = None

    if debug and not token:
        print("Warning: No `BUILDKITE_ANALYTICS_TOKEN` environment variable present", file=stderr)

    if token:
        try:
            for payload_slice in payload.into_batches(batch_size):
                response = post("https://analytics-api.buildkite.com/v1/uploads",
                                json=payload_slice.as_json(),
                                headers={
                                    "Content-Type": "application/json",
                                    "Authorization": f"Token token=\"{token}\""
                                },
                                timeout=30)
                if response.status_code >= 300:
                    return response
        except InvalidHeader as error:
            print("Warning: Invalid `BUILDKITE_ANALYTICS_TOKEN` environment variable", file=stderr)
            print(error, file=stderr)

    return response
