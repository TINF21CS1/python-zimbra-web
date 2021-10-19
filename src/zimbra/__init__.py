import logging
from typing import Optional
from dataclasses import dataclass, astuple
import uuid
import pkg_resources
import re

import requests

__version__ = '1.0'


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
    """

    def __init__(self):
        self.session_data = SessionData()

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
            'ZM_TEST': 'true',  # keine Ahnung wofür der Cookie gebraucht wird
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-GB,en;q=0.5',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://studgate.dhbw-mannheim.de',
            'Referer': 'https://studgate.dhbw-mannheim.de/',
        }

        data = {
            'loginOp': 'login',
            'username': username,
            'password': password,
            'zrememberme': '1',
            'client': 'preferred'
        }

        response = requests.post(
            'https://studgate.dhbw-mannheim.de/zimbra/', cookies=cookies, headers=headers, data=data, allow_redirects=False)
        if "ZM_AUTH_TOKEN" in response.cookies:
            self.session_data.token = response.cookies["ZM_AUTH_TOKEN"]
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

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': 'https://studgate.dhbw-mannheim.de/zimbra/h/search?mesg=welcome&init=true',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Sec-GPC': '1',
        }

        params = (
            ('si', '0'),
            ('so', '0'),
            ('sc', '709'),
            ('st', 'message'),
            ('action', 'compose'),
        )

        response = requests.get('https://studgate.dhbw-mannheim.de/zimbra/h/search', headers=headers, params=params, cookies=cookies)

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

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': 'https://studgate.dhbw-mannheim.de/zimbra/h/search?mesg=welcome&init=true',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Sec-GPC': '1',
        }

        params = (
            ('si', '0'),
            ('so', '0'),
            ('sc', '709'),
            ('st', 'message'),
            ('action', 'compose'),
        )

        response = requests.get('https://studgate.dhbw-mannheim.de/zimbra/h/search', headers=headers, params=params, cookies=cookies)
        self.session_data.jsessionid = response.cookies["JSESSIONID"]

    def send_mail(self, to: str, subject: str, body: str,
                  cc: Optional[str] = "", bcc: Optional[str] = "", replyto: Optional[str] = "", inreplyto: Optional[str] = "",
                  messageid: Optional[str] = "") -> Optional[requests.Response]:
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
                Optional[Response]: The response from the web interface, None on failure
        """
        if not self.session_data.is_valid():
            return None

        # generating uique senduid for every email.
        senduid = uuid.uuid4()
        crumb = self.get_crumb()

        if crumb is None:
            return None

        boundary = "---------------------------12839943797206379423783756262"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'Origin': 'https://studgate.dhbw-mannheim.de',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': 'https://studgate.dhbw-mannheim.de/zimbra/h/search;jsessionid=odf7pguzq1h?si=0&so=0&sc=659&st=message&action=compose',
            'Cookie': f'ZM_TEST=true; ZM_AUTH_TOKEN={self.session_data.token}; JSESSIONID={self.session_data.jsessionid}',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Sec-GPC': '1'
        }

        with open(pkg_resources.resource_filename(__name__, "templates/message.txt")) as f:
            raw = f.read()
            if "\r\n" not in raw:
                raw = raw.replace("\n", "\r\n")

        payload = raw.format(boundary=boundary, to=to, subject=subject, body=body, senduid=senduid, username=self.session_data.username,
                             cc=cc, bcc=bcc, replyto=replyto, inreplyto=inreplyto, messageid=messageid, crumb=crumb)

        url = f"https://studgate.dhbw-mannheim.de/zimbra/h/search;jsessionid={self.session_data.jsessionid}?si=0&so=0&sc=612&st=message&action=compose"
        response = requests.post(url, headers=headers, data=payload)

        return response

    @property
    def authenticated(self) -> bool:
        return self.session_data.is_valid()
