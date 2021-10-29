from zimbra import Response, ZimbraUser, WebkitAttachment
import os
import pkg_resources


def test_failing_authentication():
    username = os.environ["ZIMBRA_USERNAME"]
    password = "INCORRECT123"
    user = ZimbraUser(url="https://studgate.dhbw-mannheim.de")
    assert not user.login(username, password)
    assert not user.authenticated


def test_send_email(zimbra_user: ZimbraUser, identifier: str):
    response = zimbra_user.send_mail(f"{zimbra_user.session_data.username}@student.dhbw-mannheim.de",
                                     "[PYTEST] Zimbra Mail", f"{identifier}Hello, world!")
    assert response.success
    assert response.message == "Ihre Mail wurde gesendet."


def test_send_utf8(zimbra_user: ZimbraUser, identifier: str):
    unicodes = pkg_resources.resource_stream(__name__, "templates/unicode.txt").read().decode("utf8")
    response = zimbra_user.send_mail(f"{zimbra_user.session_data.username}@student.dhbw-mannheim.de",
                                     "[PYTEST] Unicode Test", f"{identifier}Unicodes: {unicodes}")
    assert response.success
    assert response.message == "Ihre Mail wurde gesendet."


def test_attachment_email(zimbra_user: ZimbraUser, identifier: str):
    attachment_raw = pkg_resources.resource_stream(__name__, "templates/Testbild.jpg").read()
    attachments = [WebkitAttachment(filename="Testbild.jpg", mimetype="image/jpeg", content=attachment_raw)]
    response = zimbra_user.send_mail(f"{zimbra_user.session_data.username}@student.dhbw-mannheim.de",
                                     "[PYTEST] Attachment Test", f"{identifier} Hello with attachments!", attachments=attachments)
    assert response.success
    assert response.message == "Ihre Mail wurde gesendet."


def test_send_plaineml(zimbra_user: ZimbraUser, identifier: str):
    eml = pkg_resources.resource_stream(__name__, "templates/simplemail.eml").read().decode("utf8")
    payload, boundary = zimbra_user.generate_eml_payload(eml)
    response = zimbra_user.send_raw_payload(payload, boundary)
    assert response.success
    assert response.message == "Ihre Mail wurde gesendet."