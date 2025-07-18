from random import randint
from uuid import uuid4, UUID

from buildkite_test_collector.collector.constants import VERSION
from buildkite_test_collector.collector.run_env import RunEnv, RunEnvBuilder


def test_detect_env_with_buildkite_api_env_vars_returns_the_correct_environment():
    id = str(uuid4())
    commit = uuid4().hex
    number = str(randint(0, 1000))
    job_id = str(randint(0, 1000))
    run_env = RunEnvBuilder({
        "BUILDKITE_BUILD_ID": id,
        "BUILDKITE_BUILD_URL": "https://example.test/buildkite",
        "BUILDKITE_BRANCH": "rufus",
        "BUILDKITE_COMMIT": commit,
        "BUILDKITE_BUILD_NUMBER": number,
        "BUILDKITE_JOB_ID": job_id,
        "BUILDKITE_MESSAGE": "All we are is dust in the wind, dude.",
    }).build()

    assert run_env.ci == "buildkite"
    assert run_env.key == id
    assert run_env.url == "https://example.test/buildkite"
    assert run_env.branch == "rufus"
    assert run_env.commit_sha == commit
    assert run_env.number == number
    assert run_env.job_id == job_id
    assert run_env.message == "All we are is dust in the wind, dude."


def test_detect_env_with_github_actions_env_vars_returns_the_correct_environment():
    run_number = str(randint(0, 1000))
    run_attempt = str(randint(0, 1000))
    run_id = str(uuid4())
    commit = uuid4().hex
    run_env = RunEnvBuilder({
        "GITHUB_ACTION": "bring-about-world-peace",
        "GITHUB_RUN_NUMBER": run_number,
        "GITHUB_RUN_ATTEMPT": run_attempt,
        "GITHUB_REPOSITORY": "bill-and-ted/phone-booth",
        "GITHUB_RUN_ID": run_id,
        "GITHUB_REF": "rufus",
        "GITHUB_SHA": commit,
        "TEST_ANALYTICS_COMMIT_MESSAGE": "excellent adventure"
    }).build()

    assert run_env.ci == "github_actions"
    assert run_env.key == f"bring-about-world-peace-{run_number}-{run_attempt}"
    assert run_env.url == f"https://github.com/bill-and-ted/phone-booth/actions/runs/{run_id}"
    assert run_env.branch == "rufus"
    assert run_env.commit_sha == commit
    assert run_env.number == run_number
    assert run_env.job_id is None
    assert run_env.message == "excellent adventure"

def test_detect_env_with_circle_ci_env_vars_returns_the_correct_environment():
    build_num = str(randint(0, 1000))
    workflow_id = str(uuid4())
    commit = uuid4().hex
    run_env = RunEnvBuilder({
        "CIRCLE_BUILD_NUM": build_num,
        "CIRCLE_WORKFLOW_ID": workflow_id,
        "CIRCLE_BUILD_URL": "https://example.test/circle",
        "CIRCLE_BRANCH": "rufus",
        "CIRCLE_SHA1": commit,
        "TEST_ANALYTICS_COMMIT_MESSAGE": "excellent adventure"
    }).build()

    assert run_env.ci == "circleci"
    assert run_env.key == f"{workflow_id}-{build_num}"
    assert run_env.url == "https://example.test/circle"
    assert run_env.branch == "rufus"
    assert run_env.commit_sha == commit
    assert run_env.number == build_num
    assert run_env.job_id is None
    assert run_env.message == "excellent adventure"

def test_detect_env_with_generic_env_vars():
    run_env = RunEnvBuilder({}).build()

    assert run_env.ci == "generic"
    assert UUID(run_env.key)
    assert run_env.url is None
    assert run_env.branch is None
    assert run_env.commit_sha is None
    assert run_env.number is None
    assert run_env.job_id is None
    assert run_env.message is None

def test_env_as_json(fake_env):
    json = fake_env.as_json()

    assert json["CI"] == fake_env.ci
    assert json["key"] == fake_env.key
    assert json["number"] == fake_env.number
    assert json["job_id"] == fake_env.job_id
    assert json["branch"] == fake_env.branch
    assert json["commit_sha"] == fake_env.commit_sha
    assert json["message"] == fake_env.message
    assert json["url"] == fake_env.url
    assert json["collector"] == 'python-buildkite-test-collector'
    assert json["version"] == VERSION
