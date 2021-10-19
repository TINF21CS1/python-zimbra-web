import requests
import time
import logging
import uuid  # for sendid

from typing import Optional
from dataclasses import astuple, dataclass


def current_milli_time():
    return round(time.time() * 1000)


@dataclass
class SessionData:
    token: Optional[str] = None
    username: Optional[str] = None
    # session_id: Optional[int] = None #probably replaced by jsessionid
    jsessionid: Optional[str] = None

    def is_valid(self) -> bool:
        """Returns True if no attributes are None"""
        return all(astuple(self))


def get_auth_token(username: str, password: str) -> Optional[str]:
    """
    Gets an authentication token from the Zimbra Web Client using username and password as authentication.

        Parameters:
            username (str): username to use for web authentication, without domain
            password (str): password to use for web authentication

        Returns:
            Optional[str]: The auth token if authentication was successful, None otherwise.
    """
    cookies = {
        'ZM_TEST': 'true',  # determine if cookies are enabled
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
        return response.cookies["ZM_AUTH_TOKEN"]
    else:
        if "The username or password is incorrect" in response.text:
            logging.error(
                f"Failed login attempt for user {username}: Wrong credentials")
            return None
        logging.error(f"Failed login attempt for user {username}")
        return None


def get_jsessionid(authtoken: str) -> str:
    """
    Gets a jsessionid from the authtoken

        Parameters:
            authtoken (str): Authtoken Cookie

        Returns:
            str: jsessionid string
    """

    cookies = {
        'ZM_TEST': 'true',
        'ZM_AUTH_TOKEN': authtoken,
    }

    headers = {
        'Host': 'studgate.dhbw-mannheim.de',
        'Cache-Control': 'max-age=0',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Ch-Ua': '"Chromium";v="93", " Not;A Brand";v="99"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'close',
    }

    params = (
        ('mesg', 'welcome'),
        ('init', 'true'),
    )

    response = requests.get('https://studgate.dhbw-mannheim.de/zimbra/h/search',
                            headers=headers, params=params, cookies=cookies)

    if "JSESSIONID" in response.cookies:
        return response.cookies["JSESSIONID"]
    else:
        logging.error(f"Unknown error in retrieving JSESSIONID")
        return None


def get_session_data(username: str, password: str) -> SessionData:
    """
    Gets session data from the Zimbra Web Client using username and password as authentication.

        Parameters:
            username (str): username to use for web authentication, without domain
            password (str): password to use for web authentication

        Returns:
            SessionData: Valid session data, unless an error occurred, then some values might be None.
    """
    data = SessionData(username=username)
    data.token = get_auth_token(username, password)
    if data.token is None:
        return data

    data.jsessionid = get_jsessionid(data.token)

    return data


def send_mail_as(to: str, subject: str, body: str,
                 cc: Optional[str] = "", bcc: Optional[str] = "", replyto: Optional[str] = "", inreplyto: Optional[str] = "", messageid: Optional[str] = "",
                 session_data: Optional[SessionData] = None,
                 username: Optional[str] = None, password: Optional[str] = None):
    """
    Sends an email using the supplied authentication data.

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

        Optional:
            session_data (SessionData): A valid SessionData object
            username (str): username to use for web authentication, without domain
            password (str): password to use for web authentication

        Note that either a session_data object or username and passwords needs to be supplied.
        If session_data is supplied and valid, username and password will be ignored

        Returns:
            status_code (int): The status code of the SendMailRequest
    """
    have_session_data = session_data is not None and session_data.is_valid()
    if not have_session_data and (username is None or password is None):
        raise TypeError(
            "send_mail_as() requires either valid session_data or username and password (none given)")
    if not have_session_data:
        session_data = get_session_data(username, password)
    if not session_data.is_valid():
        # TODO: probably shouldn't raise an error here and just soft-fail
        raise ValueError(
            f"authentication failed, invalid username or password?\n{session_data}")

    # generating uique senduid for every email.
    senduid = uuid.uuid4()

    boundary = "----WebKitFormBoundary2p5o8cSRRkhZkiza"

    cookies = {
        'ZM_TEST': 'true',
        'ZM_AUTH_TOKEN': session_data.token,
        'JSESSIONID': session_data.jsessionid,
    }

    headers = {
        'Host': 'studgate.dhbw-mannheim.de',
        'Cache-Control': 'max-age=0',
        'Sec-Ch-Ua': '"Chromium";v="93", " Not;A Brand";v="99"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Upgrade-Insecure-Requests': '1',
        'Origin': 'https://studgate.dhbw-mannheim.de',
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Referer': 'https://studgate.dhbw-mannheim.de/zimbra/h/search?si=0&so=0&sc=178&sfi=5&st=message&action=compose',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'close',
        'Content-Length': '3845',
    }

    params = (
        ('si', '0'),
        ('so', '0'),
        ('sc', '178'),
        ('sfi', '5'),
        ('st', 'message'),
        ('action', 'compose'),
    )

    with open("templates/message.txt") as f:
        data = f.read().format(boundary=boundary, username=username, to=to, cc=cc, bcc=bcc,
                               inreplyto=inreplyto, replyto=replyto, senduid=senduid, messageid=messageid, subject=subject, body=body)

    logging.debug(f"REQUEST:\n {headers} \n {params} \n {cookies} \n {data}")

    response = requests.post('https://studgate.dhbw-mannheim.de/zimbra/h/search',
                             headers=headers, params=params, cookies=cookies, data=data)

    logging.debug(f"RESPONSE:\n {response.text}")

    # NB. Original query string below. It seems impossible to parse and
    # reproduce query strings 100% accurately so the one below is given
    # in case the reproduced version is not "correct".
    # response = requests.post('https://studgate.dhbw-mannheim.de/zimbra/h/search?si=0&so=0&sc=178&sfi=5&st=message&action=compose', headers=headers, cookies=cookies, data=data, verify=False)

    # this request was converted from burp to curl to pyhton with https://curl.trillworks.com/
