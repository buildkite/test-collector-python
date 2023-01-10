"""Runtime environment detection"""

from dataclasses import dataclass
from typing import Dict, Optional
from uuid import uuid4
import os
from .constants import COLLECTOR_NAME, VERSION # pylint: disable=W0611

# pylint: disable=C0103 disable=R0902


def __get_env(name: str) -> Optional[str]:
    var = os.environ.get(name)
    if (var is None or var == ''):
        return None

    return var


def __buildkite_env() -> Optional['RuntimeEnvironment']:
    build_id = __get_env("BUILDKITE_BUILD_ID")

    if build_id is None:
        return None

    return RuntimeEnvironment(
        ci="buildkite",
        key=build_id,
        url=__get_env("BUILDKITE_BUILD_URL"),
        branch=__get_env("BUILDKITE_BRANCH"),
        commit_sha=__get_env("BUILDKITE_COMMIT"),
        number=__get_env("BUILDKITE_BUILD_NUMBER"),
        job_id=__get_env("BUILDKITE_JOB_ID"),
        message=__get_env("BUILDKITE_MESSAGE")
    )


def __github_actions_env() -> Optional['RuntimeEnvironment']:
    action = __get_env("GITHUB_ACTION")
    run_number = __get_env("GITHUB_RUN_NUMBER")
    run_attempt = __get_env("GITHUB_RUN_ATTEMPT")

    if (action is None or run_number is None or run_attempt is None):
        return None

    repo = __get_env("GITHUB_REPOSITORY")
    run_id = __get_env("GITHUB_RUN_ID")

    return RuntimeEnvironment(
        ci="github_actions",
        key=f"{action}-{run_number}-{run_attempt}",
        url=f"https://github.com/{repo}/actions/runs/{run_id}",
        branch=__get_env("GITHUB_REF"),
        commit_sha=__get_env("GITHUB_SHA"),
        number=run_number,
        job_id=None,
        message=None
    )


def __circle_ci_env() -> Optional['RuntimeEnvironment']:
    build_num = __get_env("CIRCLE_BUILD_NUM")
    workflow_id = __get_env("CIRCLE_WORKFLOW_ID")

    if (build_num is None or workflow_id is None):
        return None

    return RuntimeEnvironment(
        ci="circleci",
        key=f"{workflow_id}-{build_num}",
        url=__get_env("CIRCLE_BUILD_URL"),
        branch=__get_env("CIRCLE_BRANCH"),
        commit_sha=__get_env("CIRCLE_SHA1"),
        number=build_num,
        job_id=None,
        message=None
    )


def __generic_env() -> Optional['RuntimeEnvironment']:
    if __get_env("CI") is None:
        return None

    return RuntimeEnvironment(
        ci="generic",
        key=str(uuid4()),
        url=None,
        branch=None,
        commit_sha=None,
        number=None,
        job_id=None,
        message=None
    )


@dataclass(frozen=True)
class RuntimeEnvironment:
    """The detected RuntimeEnvironment"""
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
            "collector": 'python-{COLLECTOR_NAME}',
            "version": VERSION
        }

        return {k: v for k, v in attrs.items() if v is not None}


def detect_env() -> Optional['RuntimeEnvironment']:
    """Attempt to detect the CI system we're running in"""
    return __buildkite_env() or \
        __github_actions_env() or \
        __circle_ci_env() or \
        __generic_env()
