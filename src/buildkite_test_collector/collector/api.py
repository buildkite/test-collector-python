"""Buildkite Test Engine API"""

from typing import Any, Generator, Optional, Mapping
import traceback
from requests import post, Response
from requests.exceptions import InvalidHeader, HTTPError
from .payload import Payload
from ..pytest_plugin.logger import logger


# pylint: disable=too-few-public-methods
class API:
    """Buildkite Test Engine API client"""

    ENV_TOKEN = "BUILDKITE_ANALYTICS_TOKEN"
    ENV_API_URL = "BUILDKITE_ANALYTICS_API_URL"

    DEFAULT_API_URL = "https://analytics-api.buildkite.com/v1"

    def __init__(self, env: Mapping[str, Optional[str]]):
        """Initialize the API client with environment variables"""
        self.token = env.get(self.ENV_TOKEN)
        self.api_url = env.get(self.ENV_API_URL) or self.DEFAULT_API_URL

    def submit(self, payload: Payload, batch_size=100) -> Generator[Optional[Response], Any, Any]:
        """Submit a payload to the API"""
        response = None

        if not self.token:
            logger.warning("No %s environment variable present", self.ENV_TOKEN)
            yield None

        else:
            for payload_slice in payload.into_batches(batch_size):
                try:
                    response = post(self.api_url + "/uploads",
                                    json=payload_slice.as_json(),
                                    headers={
                                        "Content-Type": "application/json",
                                        "Authorization": f"Token token=\"{self.token}\""
                                    },
                                    timeout=60)
                    response.raise_for_status()
                    yield response
                except InvalidHeader as error:
                    logger.warning("Invalid %s environment variable", self.ENV_TOKEN)
                    logger.warning(error)
                    yield None
                except HTTPError as err:
                    logger.warning("Failed to uploads test results to buildkite")
                    logger.warning(err)
                    yield None
                except Exception:  # pylint: disable=broad-except
                    error_message = traceback.format_exc()
                    logger.warning(error_message)
                    yield None
