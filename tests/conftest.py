import os

from zimbra import ZimbraUser
import pytest


@pytest.fixture(scope="session")
def zimbra_user() -> ZimbraUser:
    username = os.environ["ZIMBRA_USERNAME"]
    password = os.environ["ZIMBRA_PASSWORD"]
    user = ZimbraUser()
    user.login(username, password)
    user.refresh_session_id()
    assert user.authenticated
    return user
