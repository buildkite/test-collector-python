"""Test Engine run_env"""

import platform
from dataclasses import dataclass
from typing import Dict, Optional, Mapping
from uuid import uuid4

from .constants import COLLECTOR_NAME, VERSION

# pylint: disable=too-few-public-methods
class RunEnvBuilder:
    """Builder class for RunEnv that allows injection of environment variables

    Example usage:
        # Normal usage
        builder = RunEnvBuilder(os.environ)
        env = builder.build()

        # Testing with fake environment
        fake_env = {
            "BUILDKITE_BUILD_ID": "test-build-123",
            "BUILDKITE_BUILD_URL": "https://buildkite.com/test",
            "BUILDKITE_BRANCH": "main",
            "BUILDKITE_COMMIT": "abc123",
        }
        builder = RunEnvBuilder(fake_env)
        env = builder.build()
        assert env.ci == "buildkite"
        assert env.key == "test-build-123"
    """

    def __init__(self, env: Mapping[str, Optional[str]]):
        self.env = env

    def build(self) -> 'RunEnv':
        """Build a RunEnv by detecting the CI system"""
        return \
            self._buildkite_env() or \
            self._github_actions_env() or \
            self._circle_ci_env() or \
            self._generic_env()

    def _get_env(self, name: str) -> Optional[str]:
        var = self.env.get(name)
        if (var is None or var == ''):
            return None
        return var

    def _buildkite_env(self) -> Optional['RunEnv']:
        build_id = self._get_env("BUILDKITE_BUILD_ID")

        if build_id is None:
            return None

        return RunEnv(
            ci="buildkite",
            key=build_id,
            url=self._get_env("BUILDKITE_BUILD_URL"),
            branch=self._get_env("BUILDKITE_BRANCH"),
            commit_sha=self._get_env("BUILDKITE_COMMIT"),
            number=self._get_env("BUILDKITE_BUILD_NUMBER"),
            job_id=self._get_env("BUILDKITE_JOB_ID"),
            message=self._get_env("BUILDKITE_MESSAGE")
        )

    def _github_actions_env(self) -> Optional['RunEnv']:
        action = self._get_env("GITHUB_ACTION")
        run_number = self._get_env("GITHUB_RUN_NUMBER")
        run_attempt = self._get_env("GITHUB_RUN_ATTEMPT")

        if (action is None or run_number is None or run_attempt is None):
            return None

        repo = self._get_env("GITHUB_REPOSITORY")
        run_id = self._get_env("GITHUB_RUN_ID")

        return RunEnv(
            ci="github_actions",
            key=f"{action}-{run_number}-{run_attempt}",
            url=f"https://github.com/{repo}/actions/runs/{run_id}",
            branch=self._get_env("GITHUB_REF"),
            commit_sha=self._get_env("GITHUB_SHA"),
            number=run_number,
            job_id=None,
            message=self._get_env("TEST_ANALYTICS_COMMIT_MESSAGE"),
        )

    def _circle_ci_env(self) -> Optional['RunEnv']:
        build_num = self._get_env("CIRCLE_BUILD_NUM")
        workflow_id = self._get_env("CIRCLE_WORKFLOW_ID")

        if (build_num is None or workflow_id is None):
            return None

        return RunEnv(
            ci="circleci",
            key=f"{workflow_id}-{build_num}",
            url=self._get_env("CIRCLE_BUILD_URL"),
            branch=self._get_env("CIRCLE_BRANCH"),
            commit_sha=self._get_env("CIRCLE_SHA1"),
            number=build_num,
            job_id=None,
            message=self._get_env("TEST_ANALYTICS_COMMIT_MESSAGE"),
        )

    def _generic_env(self) -> 'RunEnv':
        return RunEnv(
            ci="generic",
            key=str(uuid4()),
            url=None,
            branch=None,
            commit_sha=None,
            number=None,
            job_id=None,
            message=None
        )


# pylint: disable=too-many-instance-attributes
@dataclass(frozen=True)
class RunEnv:
    """The detected RunEnv"""
    ci: str
    key: str
    number: Optional[str]
    job_id: Optional[str]
    branch: Optional[str]
    commit_sha: Optional[str]
    message: Optional[str]
    url: Optional[str]

    def as_json(self) -> Dict[str, str]:
        """Convert this trace into a Dict for eventual serialisation into JSON"""
        attrs = {
            "CI": self.ci,
            "key": self.key,
            "number": self.number,
            "job_id": self.job_id,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "message": self.message,
            "url": self.url,
            "collector": COLLECTOR_NAME,
            "version": VERSION,
            "language_version": f"{platform.python_version()}"
        }

        return {k: v for k, v in attrs.items() if v is not None}
