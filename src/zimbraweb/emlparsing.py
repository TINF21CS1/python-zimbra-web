from typing import Tuple, List, Dict, Any
import re
import base64

from email.parser import Parser
import email
from zimbraweb import ZimbraUser, WebkitAttachment


def parse_eml(user: ZimbraUser, eml: str) -> Tuple[bytes, str]:
    """Generate a payload from any eml

    Args:
        user (ZimbraUser): Zimbra user that sent the eml
        eml (str): str

    Returns:
        bytes: The WebkitFormBoundary Payload
        str: The boundary used in the payload
    """

    parser = Parser()
    parsed = parser.parsestr(eml)

    if type(parsed.get_payload()) == str:
        return user.generate_webkit_payload(parsed['To'], parsed['Subject'], parsed.get_payload())

    elif type(parsed.get_payload()) == list:
        dict_mail = {}
        dict_mail['to'] = parsed['To']
        dict_mail['subject'] = parsed['Subject']
        dict_mail['body'] = []  # we later only want one entry in body, but first we collect all body entries to then get the one we want
        dict_mail['attachments'] = []

        # parsing body and attachments to dictionary
        dict_mail = parse_multipart_eml(user, parsed.get_payload(), dict_mail)

        # at this point dict_mail['body'] is a list of email.message.Message objects

        # parsing bodies
        if len(dict_mail['body']) == 0:  # no body
            dict_mail['body'] = ""
        elif len(dict_mail['body']) == 1:  # one body
            dict_mail['body'] = dict_mail['body'][0].get_payload()
        elif len(dict_mail['body']) > 1:  # more than one body
            for b in dict_mail['body']:
                if b.get('Content-Type')[:b.get('Content-Type').find(";")] == "text/plain":
                    body = b.get_payload()
            dict_mail['body'] = body

        return user.generate_webkit_payload(**dict_mail)

    else:
        raise TypeError()
        # dont know when this happens, but just to be sure


def parse_multipart_eml(user: ZimbraUser, payload: List[email.message.Message], dict_mail: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a dictionary of multipart-parts form a multipart email payload

    Args:
        user (ZimbraUser): Zimbra user that sent the eml
        parsedcontent (dict): an existing dictionary, key 'body' contains the body, key 'attachments' contains a [WebkitAttachments] list of attachments
        payload (list): list of email message objects

    Returns:
        dict: A dictionary with body and attachments
    """

    for p in payload:
        # multipart recursion
        if type(p.get_payload()) == list:
            dict_mail = parse_multipart_eml(user, p.get_payload(), dict_mail)

        else:
            # body
            if "attachment" not in p.get('Content-Disposition', ''):
                dict_mail['body'].append(p)

            # attachment
            if "attachment" in p.get('Content-Disposition', ''):
                dict_mail['attachments'].append(WebkitAttachment(
                    mimetype=p.get('Content-Type')[:p.get('Content-Type').find(";")],
                    filename=re.findall('filename=\"(.*?)\"', p.get('Content-Disposition'))[0],
                    content=base64.b64decode(p.get_payload())
                ))

    return dict_mail
