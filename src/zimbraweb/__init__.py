import logging
from typing import Optional, Dict, Tuple, List
from dataclasses import dataclass, astuple
import uuid
import re
import random
import string
import time

import requests

import zimbraweb.emlparsing

__version__ = '2.1.0'


@dataclass
class WebkitAttachment:
    """
    Represents a single attachment for WebkitFormBoundary data.

    Attributes:
        filename (str): The name of the attachment
        mimetype (str): The Mimetype, e.g. image/jpeg.
        content (bytes): The raw bytes of the attachment.
    """
    filename: str
    mimetype: str
    content: bytes

    def get_webkit_payload(self) -> bytes:
        payload = f'Content-Disposition: form-data; name="fileUpload"; filename="{self.filename}"\r\nContent-Type: {self.mimetype}\r\n\r\n'.encode("utf8")
        payload += self.content
        return payload


@dataclass
class Response:
    """
    Helper class to return a success bool and a status message.
    """
    success: bool = False
    message: str = ""


@dataclass
class SessionData:
    """
    Holds all authentication session data for a single Zimbra web user.

    Attributes:
        token (Optional[str]): A ZM_AUTH_TOKEN cookie, if authenticated.
        expires (Optional[int]): The unixtime expiration date of the auth token.
        jsessionid (Optional[str]): A JSESSIONID cookie, if a session has been opened.
        username (Optional[str]): The username of the authenticated user, if authenticated.
        from_address (Optional[str]): The default sender address used by the Zimbra web interface, if authenticated.
        crumb (Optional[str]): The validation crumb needed to generate payloads, if authenticated.
    """
    token: Optional[str] = None
    expires: Optional[int] = None
    jsessionid: Optional[str] = None
    username: Optional[str] = None
    from_address: Optional[str] = None
    crumb: Optional[str] = None

    def is_valid(self) -> bool:
        """Returns True if no attributes are None and auth token is still valid."""
        if all(astuple(self)):
            # coverd by all(...) but mypy doesn't understand: https://github.com/python/mypy/issues/11339#issuecomment-943970226
            assert self.expires is not None

            return self.expires > int(time.time())
        return False

    def as_cookies(self) -> Dict[str, str]:
        """Returns a dictionary containting ZM_TEST, ZM_AUTH_TOKEN, JSESSIONID."""
        cookies = {"ZM_TEST": 'true'}
        if self.token is not None:
            cookies["ZM_AUTH_TOKEN"] = self.token
        if self.jsessionid is not None:
            cookies["JSESSIONID"] = self.jsessionid
        return cookies


class ZimbraUser:
    """This class represent a single user instance on the Zimbra Web Interface."""

    _headers: Dict[str, str] = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-GB,en;q=0.5',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    def __init__(self, url: str):
        """
        Creates a new user instance for the Zimbra Web Client. This does not actually contact the web client yet.

        Args:
            url (str): The URL on which zimbra is hosted (i.e. where the login page is located)
        """
        self.session_data = SessionData()
        self.url = url

    def logout(self) -> bool:
        """
        Logs the user out of the web client and invalidates any session data.

        Returns:
            True if logout was successful
        """
        if not self.session_data.is_valid():
            return False
        params = (
              ('loginOp', 'logout'),
        )

        requests.get(
            f'{self.url}/zimbra/', headers=self._headers, params=params, cookies=self.session_data.as_cookies())
        self.session_data = SessionData()   # maybe search response if auth-token expired/not valid??
        return True

    def login(self, username: str, password: str) -> bool:
        """
        Gets an authentication token from the Zimbra Web Client using username and password as authentication.

        Args:
            username (str): username to use for web authentication, without domain
            password (str): password to use for web authentication

        Returns:
            True if authentication was successful
        """
        self.session_data.username = username

        data = {
            'loginOp': 'login',
            'username': username,
            'password': password,
            'zrememberme': '1',
            'client': 'preferred'
        }

        response = requests.post(
            f'{self.url}/zimbra/', cookies=self.session_data.as_cookies(), headers=self._headers, data=data, allow_redirects=False)
        if "ZM_AUTH_TOKEN" in response.cookies:
            self.session_data.token = response.cookies["ZM_AUTH_TOKEN"]
            for cookie in response.cookies:
                if cookie.name == "ZM_AUTH_TOKEN":
                    self.session_data.expires = cookie.expires
            self.session_data.jsessionid = self.get_session_id()
            mail_info = self.get_mail_info()
            if mail_info is None:
                return False
            self.session_data.crumb = mail_info["crumb"]
            self.session_data.from_address = mail_info["from_address"]
            return self.authenticated
        else:
            if "The username or password is incorrect" in response.text:
                logging.error(f"Failed login attempt for user {username}: Wrong credentials")
                return False
            logging.error(f"Failed login attempt for user {username}")
            return False

    def get_mail_info(self) -> Optional[Dict[str, str]]:
        """
        Gets a valid crumb and from header to send an email

            Returns:
                Optional[Dict[str, str]]: {'crumb': 'xxx', 'from_header': 's00000@domain.com'} or None
        """

        if not self.session_data.token or not self.session_data.jsessionid:
            return None

        params = (
            ('si', '0'),
            ('so', '0'),
            ('sc', '709'),
            ('st', 'message'),
            ('action', 'compose'),
        )

        response = requests.get(f'{self.url}/zimbra/h/search', headers=self._headers, params=params, cookies=self.session_data.as_cookies())

        crumb_matches = re.findall('<input type="hidden" name="crumb" value="(.*?)"/>', response.text)
        if len(crumb_matches) == 0:
            return None
        crumb = str(crumb_matches[0])
        from_address_matches = re.findall('<input type="hidden" name="from" value="(.*?)"/>', response.text)
        if len(from_address_matches) == 0:
            return None
        from_header = str(from_address_matches[0].replace("&#034;", "\"").replace("&lt;", "<").replace("&gt;", ">"))
        return {"crumb": crumb, "from_address": from_header}

    def get_session_id(self) -> Optional[str]:
        """
        Gets a new session id for the current user.

        Returns:
            A new JESSIONID or None if an error occurred.
        """

        params = (
            ('si', '0'),
            ('so', '0'),
            ('sc', '709'),
            ('st', 'message'),
            ('action', 'compose'),
        )

        response = requests.get(f'{self.url}/zimbra/h/search', headers=self._headers, params=params, cookies=self.session_data.as_cookies())
        if "JSESSIONID" in response.cookies:
            return str(response.cookies["JSESSIONID"])
        else:
            return None

    def generate_webkit_payload(self, to: str, subject: str, body: str, attachments: List[WebkitAttachment] = [], **kwargs) -> Tuple[bytes, str]:
        """Generate a WebkitFormBoundary payload

        Args:
            to (str): Recipient.
            subject (str): Email Subject Header.
            body (str): plain/text email body.
            attachments (List[zimbraweb.WebkitAttachment]): List of attachments to add to the payload.
            **kwargs: Extended Mail Parameters (cc, bcc, replyto, inreplyto, messageid) can be set via kwargs.

        Returns:
            A Tuple (payload [bytes], boundary [str])
        """

        # generating uique senduid for every email.
        senduid = uuid.uuid4()

        boundary = "----WebKitFormBoundary" + ''.join(random.sample(string.ascii_letters + string.digits, 16))

        # adding the send action
        payload = f'--{boundary}\r\nContent-Disposition: form-data; name="actionSend"\r\n\r\nSenden\r\n'.encode("utf8")

        for attachment in attachments:
            payload += f'--{boundary}\r\n'.encode("utf8") + attachment.get_webkit_payload() + "\r\n".encode("utf8")

        mail_props = {"from": self.session_data.from_address, "to": to, "subject": subject,
                      "body": body, **kwargs, "senduid": senduid, "crumb": self.session_data.crumb}

        for prop_name, prop_value in mail_props.items():
            payload += f'--{boundary}\r\nContent-Disposition: form-data; name="{prop_name}"\r\n\r\n{prop_value}\r\n'.encode("utf8")

        # adding last boundary
        payload += f'--{boundary}--\r\n'.encode("utf8")
        return payload, boundary

    def send_eml(self, eml: str) -> Response:
        """
        Tries to send an email from a .eml file.

        Args:
            eml (str): The EML string to send

        Returns:
            A zimbraweb.Response object with response.success == True if payload was sent successfully and the resposne message from the web client.
        """

        # mypy doesn't like the dict unpacking because it cannot check the types.
        payload, boundary = self.generate_webkit_payload(**zimbraweb.emlparsing.parse_eml(eml))  # type: ignore
        return self.send_raw_payload(payload=payload, boundary=boundary)

    def send_raw_payload(self, payload: bytes, boundary: str) -> Response:
        """
        Sends a raw payload to the Web interface.

        Examples:
            >>> from zimbraweb import ZimbraUser
            >>> user = ZimbraUser("https://my-zimbra.server")
            >>> user.login("xxx", "xxx")
            >>> payload, boundary = user.generate_webkit_payload(to="hello@example.com", subject="test mail", body="hello, world!")
            >>> user.send_raw_payload(payload, boundary)
            Response(success=True, status="Ihre Mail wurde gesendet.")

        Args:
            payload (bytes): The payload to send in the body of the request
            boundary (str): The boundary that is used in the WebkitFormBoundary payload

        Returns:
            A zimbraweb.Response object with response.success == True if payload was sent successfully and the resposne message from the web client.
        """
        if not self.authenticated:
            return Response(False, "Not Authenticated")

        headers = {**self._headers,
                   'Content-Type': f'multipart/form-data; boundary={boundary}',
                   'Cookie': f'ZM_TEST=true; ZM_AUTH_TOKEN={self.session_data.token}; JSESSIONID={self.session_data.jsessionid}',
                   }

        url = f"{self.url}/zimbra/h/search;jsessionid={self.session_data.jsessionid}?si=0&so=0&sc=612&st=message&action=compose"
        response = requests.post(url, headers=headers, data=payload)

        # finding the status in the response
        zresponsestatus = re.findall('<td class="Status" nowrap="nowrap">\n            &nbsp;(.*?)\n        </td>', response.text)

        if len(zresponsestatus) == 0:
            logging.error("Website content returned no status.\n{response}")
            return Response(False, "Unknown Error")
        else:
            status_msg = str(zresponsestatus[0])
            logging.info(status_msg)
            success = status_msg == "Ihre Mail wurde gesendet."
            return Response(success, status_msg)

    def send_mail(self, to: str, subject: str, body: str, attachments: List[WebkitAttachment] = [], **kwargs) -> Response:
        """
        Sends an email as the current user.

        Args:
            to (str): Recipient.
            subject (str): Email Subject Header.
            body (str): plain/text email body.
            attachments (List[zimbraweb.WebkitAttachment]): List of attachments to send with the email.
            **kwargs: Extended Mail Parameters (cc, bcc, replyto, inreplyto, messageid) can be set via kwargs.

        Returns:
            A zimbraweb.Response object containing the status message of the server
            and response.success = True if the email was sent successfully.
        """
        payload, boundary = self.generate_webkit_payload(to=to, subject=subject, body=body, attachments=attachments, **kwargs)
        return self.send_raw_payload(payload, boundary)

    @property
    def authenticated(self) -> bool:
        """Is the user authenticated with the web client?"""
        return self.session_data.is_valid()
