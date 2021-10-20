"""# Zimbra

Only 1 class: `ZimbraUser`

Usage example:
```python
>>> from zimbra import ZimbraUser
>>> user = ZimbraUser("https://myzimbra.server")
>>> user.login("s000000", "hunter2")
>>> user.send_mail(from_header="Me <me@myzimbra.server>", to="receiver@example.com", subject="subject", body="body")
```
"""
import logging
from typing import Optional, Dict
from dataclasses import dataclass, astuple
import uuid
import pkg_resources
import re
import random
import string
import email.utils

import requests

__version__ = '1.0.1'


@dataclass
class SessionData:
    token: Optional[str] = None
    jsessionid: Optional[str] = None
    username: Optional[str] = None

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
    >>> user.send_mail(from_header="Me <me@myzimbra.server>", to="receiver@example.com", subject="subject", body="body")
    ```

    methods:
    ```python
    # Login as a user. Returns True on success: 
    user.login(username: str, password: str) -> bool
    
    # Gets a new JSESSIONID Cookie for the current user:
    user.refresh_session_id() -> None

    # Try to get a crumb for the current user:
    user.get_crumb() -> Optional[str]

    # Checks if the current user is allowed to send as `from_header`:
    user.allowed_from_header(from_header: str) -> bool

    # Send an email from the current user account:
    send_mail(from_header: str, to: str, subject: str, body: str,
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
            self.refresh_session_id()
            return True
        else:
            if "The username or password is incorrect" in response.text:
                logging.error(
                    f"Failed login attempt for user {username}: Wrong credentials")
                return False
            logging.error(f"Failed login attempt for user {username}")
            return False

    def get_crumb(self) -> Optional[str]:
        """
        Gets a valid crumb to send an email

            Returns:
                Optional[str]: A crumb if authenticated, None otherwise
        """

        if not self.authenticated:
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

        crumb = re.findall('<input type="hidden" name="crumb" value="(.*?)"/>', response.text)
        if len(crumb) == 0:
            return None
        else:
            return str(crumb[0])

    def refresh_session_id(self):
        """
        Sets a new session id for the current session.
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
        self.session_data.jsessionid = response.cookies["JSESSIONID"]

    def allowed_from_header(self, from_header: str) -> bool:
        """
        Checks if the current logged-in user is allowed to send as from_header
            Parameters:
                from_header (str): A RFC-822 compliant email from: header

            Returns:
                bool: True if the user is allowed to send from this header
        """
        if self.session_data.username is None:
            # if we don't have a user, don't send as anyone
            return False
        parsed_from_header = email.utils.parseaddr(from_header)
        if not from_header.count("<") == 1 and from_header.count(">") == 1:
            # there might be multiple emails in this header: "Name <email1@email1.com> <email2@email2.com>" -> disallow
            return False
        # we're only allowed to send from: "<{username}@...>", with any name "Any Name <...>"
        # FIXME: currently allows sending from ANY email domain
        return self.session_data.username + "@" in parsed_from_header[1]

    def send_mail(self, from_header: str, to: str, subject: str, body: str,
                  cc: Optional[str] = "", bcc: Optional[str] = "", replyto: Optional[str] = "", inreplyto: Optional[str] = "",
                  messageid: Optional[str] = "") -> Optional[requests.Response]:
        """
        Sends an email as the current user.

            Parameters:
                from_header (str): Apparent sender
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
                Optional[Response]: The response from the web interface, None on failure
        """
        if not self.session_data.is_valid():
            return None

        # make sure the from header looks valid and is owned by the sender to prevent spoofing
        if not self.allowed_from_header(from_header):
            logging.warn(f"User {self.session_data.username} tried to send as {from_header} but was not allowed.")
            return None

        # generating uique senduid for every email.
        senduid = uuid.uuid4()
        crumb = self.get_crumb()

        if crumb is None:
            return None

        boundary = "----WebKitFormBoundary" + ''.join(random.sample(string.ascii_letters + string.digits, 16))

        headers = {**self._headers,
                   'Content-Type': f'multipart/form-data; boundary={boundary}',
                   'Cookie': f'ZM_TEST=true; ZM_AUTH_TOKEN={self.session_data.token}; JSESSIONID={self.session_data.jsessionid}',
                   }

        with open(pkg_resources.resource_filename(__name__, "templates/message.txt")) as f:
            raw = f.read()
            if "\r\n" not in raw:
                raw = raw.replace("\n", "\r\n")

        payload = raw.format(boundary=boundary, from_header=from_header, to=to, subject=subject, body=body, senduid=senduid,
                             cc=cc, bcc=bcc, replyto=replyto, inreplyto=inreplyto, messageid=messageid, crumb=crumb)

        url = f"{self.url}/zimbra/h/search;jsessionid={self.session_data.jsessionid}?si=0&so=0&sc=612&st=message&action=compose"
        response = requests.post(url, headers=headers, data=payload)

        return response

    @property
    def authenticated(self) -> bool:
        return self.session_data.is_valid()
