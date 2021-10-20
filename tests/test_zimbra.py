from zimbra import ZimbraUser
import os
import uuid
import pkg_resources


def test_failing_authentication():
    username = os.environ["ZIMBRA_USERNAME"]
    password = "INCORRECT123"
    user = ZimbraUser(url="https://studgate.dhbw-mannheim.de")
    assert not user.login(username, password)
    assert not user.authenticated


def test_send_email(zimbra_user: ZimbraUser):
    identifier = uuid.uuid4()
    response = zimbra_user.send_mail(to=f"{zimbra_user.session_data.username}@student.dhbw-mannheim.de",
                                     subject=f"Test Mail {identifier}", body=f"This is a test mail with the identifier {identifier}")
    assert response is not None
    assert response.status_code == 200
    assert "Ihre Mail wurde gesendet" in response.text


def test_send_utf8(zimbra_user: ZimbraUser):
    identifier = uuid.uuid4()
    unicodes = pkg_resources.resource_stream(__name__, "templates/unicode.txt").read().decode("utf8")
    response = zimbra_user.send_mail(f"{zimbra_user.session_data.username}@student.dhbw-mannheim.de",
                                     f"Test Mail {identifier}", f"This is a test mail with the identifier {identifier}. Unicodes: {unicodes}")
    assert response.status_code == 200
    assert "Ihre Mail wurde gesendet" in response.text
