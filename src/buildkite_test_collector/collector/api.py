"""Buildkite Test Analytics API"""

from typing import Optional
from os import environ
from requests import post, Response
from .payload import Payload


def submit(payload: Payload, batch_size=100) -> Optional[Response]:
    """Submit a payload to the API"""
    token = environ.get("BUILDKITE_ANALYTICS_TOKEN")
    response = None

    if token:
        for payload_slice in payload.into_batches(batch_size):
            response = post("https://analytics-api.buildkite.com/v1/uploads",
                            json=payload_slice.as_json(),
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Token token=\"{token}\""
                            })
            if response.status_code >= 300:
                return response

    return response
