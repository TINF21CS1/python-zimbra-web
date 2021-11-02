import os

from zimbraweb import ZimbraUser
import pytest


@pytest.fixture()
def zimbra_user() -> ZimbraUser:
    username = os.environ["ZIMBRA_USERNAME"]
    password = os.environ["ZIMBRA_PASSWORD"]
    user = ZimbraUser(url="https://studgate.dhbw-mannheim.de")
    assert user.login(username, password)
    assert user.authenticated
    return user


@pytest.fixture(scope="session")
def identifier() -> str:
    if "CI" in os.environ:
        # we're in CI
        unk = "<UNKNOWN>"
        repo = os.environ.get("GITHUB_REPOSITORY", unk)
        workflow = os.environ.get("GITHUB_WORKFLOW", unk)
        action_id = os.environ.get("GITHUB_ACTION", unk)
        run_id = os.environ.get("GITHUB_RUN_ID", unk)
        ref = os.environ.get("GITHUB_REF", unk)
        sha = os.environ.get("GITHUB_SHA", unk)

        return f"""
[PYTEST] This is a test running in CI. Here's what I know:

Repository: {repo}
workflow: {workflow}
action: {action_id}
run_id: {run_id}
ref: {ref}
sha: {sha}
---
"""
    else:
        return "[PYTEST] This is a test running locally on " + os.environ.get("COMPUTERNAME", "UNKNOWN") + "\n---\n"
