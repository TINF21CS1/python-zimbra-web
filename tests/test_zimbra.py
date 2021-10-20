from zimbra import ZimbraUser
import os
import uuid


def test_failing_authentication():
    username = os.environ["ZIMBRA_USERNAME"]
    password = "INCORRECT123"
    user = ZimbraUser(url="https://studgate.dhbw-mannheim.de")
    assert not user.login(username, password)
    assert not user.authenticated


def test_send_email(zimbra_user: ZimbraUser):
    identifier = uuid.uuid4()
    response = zimbra_user.send_mail(f"{zimbra_user.session_data.username}@student.dhbw-mannheim.de",
                                     f"Test Mail {identifier}", f"This is a test mail with the identifier {identifier}")
    assert response == "Ihre Mail wurde gesendet."
