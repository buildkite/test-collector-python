"""Buildkite Test Analytics API"""

from typing import Optional
from os import environ
import traceback
from requests import post, Response
from requests.exceptions import InvalidHeader, HTTPError
from .payload import Payload
from ..pytest_plugin.logger import logger


def submit(payload: Payload, batch_size=100) -> Optional[Response]:
    """Submit a payload to the API"""
    token = environ.get("BUILDKITE_ANALYTICS_TOKEN")
    api_url = environ.get("BUILDKITE_ANALYTICS_API_URL", "https://analytics-api.buildkite.com/v1")
    response = None

    if not token:
        logger.warning("No `BUILDKITE_ANALYTICS_TOKEN` environment variable present")

    if token:
        try:
            for payload_slice in payload.into_batches(batch_size):
                response = post(api_url + "/uploads",
                                json=payload_slice.as_json(),
                                headers={
                                    "Content-Type": "application/json",
                                    "Authorization": f"Token token=\"{token}\""
                                },
                                timeout=60)
                response.raise_for_status()
                return response
        except InvalidHeader as error:
            logger.warning("Invalid `BUILDKITE_ANALYTICS_TOKEN` environment variable")
            logger.warning(error)
        except HTTPError as err:
            logger.warning("Failed to uploads test results to buildkite")
            logger.warning(err)
        except Exception:  # pylint: disable=broad-except
            error_message = traceback.format_exc()
            logger.warning(error_message)
    return None
