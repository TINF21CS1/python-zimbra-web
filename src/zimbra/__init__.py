"""# Zimbra

Usage example:
```python
>>> from zimbra import ZimbraUser
>>> user = ZimbraUser("https://myzimbra.server")
>>> user.login("s000000", "hunter2")
>>> user.send_mail(to="receiver@example.com", subject="subject", body="body")
```
"""
import logging
from typing import Optional, Dict, Tuple
from dataclasses import dataclass, astuple
import uuid
import pkg_resources
import re
import random
import string

import requests

__version__ = '1.0.1'


@dataclass
class Response:
    success: bool = False
    message: str = ""


@dataclass
class SessionData:
    token: Optional[str] = None
    jsessionid: Optional[str] = None
    username: Optional[str] = None
    from_address: Optional[str] = None
    crumb: Optional[str] = None

    def is_valid(self) -> bool:
        """Returns True if no attributes are None"""
        return all(astuple(self))


class ZimbraUser:
    """
    This class represent a single user instance on the Zimbra Web Interface.

    usage example:
    ```python
    >>> user = ZimbraUser("https://myzimbra.server")
    >>> user.login("s000000", "hunter2")
    >>> user.send_mail(to="receiver@example.com", subject="subject", body="body")
    ```

    methods:
    ```python
    # Login as a user. Returns True on success:
    user.login(username: str, password: str) -> bool

    # Gets a new JSESSIONID Cookie for the current user:
    user.get_session_id() -> Optional[str]

    # Try to get a crumb and the from address for the current user:
    user.get_mail_info() -> Optional[Dict[str, str]]

    # Send an email from the current user account:
    send_mail(to: str, subject: str, body: str,
              cc: Optional[str] = "", bcc: Optional[str] = "", replyto: Optional[str] = "",
              inreplyto: Optional[str] = "", messageid: Optional[str] = "")
              -> Optional[requests.Response]
    ```

    properties:

    `authenticated (bool)`: True if this instance is authenticated with the Zimbra Web Interface
    """
    _headers: Dict[str, str] = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-GB,en;q=0.5',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    def __init__(self, url: str):
        """
        Parameters:
            url - The URL on which zimbra is hosted (i.e. where the login page is located)
        """
        self.session_data = SessionData()
        self.url = url

    def login(self, username: str, password: str) -> bool:
        """
        Gets an authentication token from the Zimbra Web Client using username and password as authentication.

            Parameters:
                username (str): username to use for web authentication, without domain
                password (str): password to use for web authentication

            Returns:
                bool: True if authentication was successful
        """
        self.session_data.username = username

        cookies = {
            'ZM_TEST': 'true',  # determine if cookies are enabled
        }

        data = {
            'loginOp': 'login',
            'username': username,
            'password': password,
            'zrememberme': '1',
            'client': 'preferred'
        }

        response = requests.post(
            f'{self.url}/zimbra/', cookies=cookies, headers=self._headers, data=data, allow_redirects=False)
        if "ZM_AUTH_TOKEN" in response.cookies:
            self.session_data.token = response.cookies["ZM_AUTH_TOKEN"]
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

        cookies = {
            'ZM_TEST': 'true',
            'ZM_AUTH_TOKEN': self.session_data.token,
            'JSESSIONID': self.session_data.jsessionid
        }

        params = (
            ('si', '0'),
            ('so', '0'),
            ('sc', '709'),
            ('st', 'message'),
            ('action', 'compose'),
        )

        response = requests.get(f'{self.url}/zimbra/h/search', headers=self._headers, params=params, cookies=cookies)

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
        """

        cookies = {
            'ZM_TEST': 'true',
            'ZM_AUTH_TOKEN': self.session_data.token,
        }

        params = (
            ('si', '0'),
            ('so', '0'),
            ('sc', '709'),
            ('st', 'message'),
            ('action', 'compose'),
        )

        response = requests.get(f'{self.url}/zimbra/h/search', headers=self._headers, params=params, cookies=cookies)
        if "JSESSIONID" in response.cookies:
            return str(response.cookies["JSESSIONID"])
        else:
            return None

    def generate_webkit_payload(self, to: str, subject: str, body: str,
                                cc: Optional[str] = "", bcc: Optional[str] = "", replyto: Optional[str] = "", inreplyto: Optional[str] = "",
                                messageid: Optional[str] = "") -> Tuple[bytes, str]:
        """Generate a WebkitFormBoundary payload

            Parameters:
                to (str): Recipient
                subject (str): Email Subject Header
                body (str): plain/text email body

            Extended Mail Parameters:
                cc (str): CC-Recipient
                bcc (str): BCC-Recipient
                replyto (str): Reply-To E-Mail field
                inreplyto (str): Message-ID of previous E-Mail
                messageid(str): Message-ID of this E-Mail. If none is passed, it will be generated by Zimbra


            Returns:
                bytes: The WebkitFormBoundary Payload
                str: The boundary used in the payload
        """

        # generating uique senduid for every email.
        senduid = uuid.uuid4()

        boundary = "----WebKitFormBoundary" + ''.join(random.sample(string.ascii_letters + string.digits, 16))

        with open(pkg_resources.resource_filename(__name__, "templates/message.txt")) as f:
            raw = f.read()
        if "\r\n" not in raw:
            raw = raw.replace("\n", "\r\n")

        # Variablen für Attachments sind: filecontent, filename, mimetype

        #reading binary attachment form file
        with open(pkg_resources.resource_filename(__name__, "templates/Testanhang.txt"), "rb") as f:
            filecontent = f.read() # reads raw
        #the attachment variables are hardcoded for testing right now
        filename="Testanhang.txt"
        mimetype="text/plain"

        payload = raw.format(boundary=boundary, from_header=self.session_data.from_address, to=to, subject=subject, body=body, senduid=senduid,
                             cc=cc, bcc=bcc, replyto=replyto, inreplyto=inreplyto, messageid=messageid, crumb=self.session_data.crumb,
                             filename=filename, filecontent=filecontent, mimetype=mimetype)
        return payload.encode("utf8"), boundary

    def send_raw_payload(self, payload: bytes, boundary: str) -> Response:
        """
        Sends a raw payload to the Web interface.

            Parameters:
                payload (bytes): The payload to send in the body of the request
                boundary (str): The boundary that is used in the WebkitFormBoundary payload

            Returns:
                Response: A zimbra.Response object with response.True if payload was sent successfully
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

    def send_mail(self, to: str, subject: str, body: str,
                  cc: Optional[str] = "", bcc: Optional[str] = "", replyto: Optional[str] = "", inreplyto: Optional[str] = "",
                  messageid: Optional[str] = "") -> Response:
        """
        Sends an email as the current user.

            Parameters:
                to (str): Recipient
                subject (str): Email Subject Header
                body (str): plain/text email body

            Extended Mail Parameters:
                cc (str): CC-Recipient
                bcc (str): BCC-Recipient
                replyto (str): Reply-To E-Mail field
                inreplyto (str): Message-ID of previous E-Mail
                messageid(str): Message-ID of this E-Mail. If none is passed, it will be generated by Zimbra


            Returns:
                Response: A zimbra.Response object
        """
        payload, boundary = self.generate_webkit_payload(to=to, subject=subject, body=body, cc=cc, bcc=bcc,
                                                         replyto=replyto, inreplyto=inreplyto, messageid=messageid)
        return self.send_raw_payload(payload, boundary)

    @property
    def authenticated(self) -> bool:
        return self.session_data.is_valid()
