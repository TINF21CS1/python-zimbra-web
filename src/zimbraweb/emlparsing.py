import logging
from typing import Optional, Dict, Tuple, List
import string
import uuid
import re
import base64
import random

from email.parser import Parser

from zimbraweb import ZimbraUser, WebkitAttachment  # for parsing eml

def eml_parsing(user: ZimbraUser, eml: str) -> Tuple[bytes, str]:
    """Generate a payload from any eml

        Parameters:
            user: ZimbraUser Class
            eml: str

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
        dict_mail['attachments'] = []
        return user.generate_webkit_payload(**multipart_eml_parsing(user, parsed.get_payload(), dict_mail))

    else:
        raise TypeError("Multipart Payload in Plain Parser. Please use multipart_eml_parsing")


def plain_eml_parsing(user: ZimbraUser, eml: str) -> Tuple[bytes, str]:
    # right now this function is useless, since its so short and basically needs to be done for eml_parsing function anyway
    """Generate a payload from plaintext eml

        Parameters:
            user: ZimbraUser Class
            eml: str

        Returns:
            bytes: The WebkitFormBoundary Payload
            str: The boundary used in the payload
    """

    parser = Parser()
    parsed = parser.parsestr(eml)

    # this if is not strictly necessary, but prevents from calling the plain function for multipart messages
    if type(parsed.get_payload()) == str:
        return user.generate_webkit_payload(parsed['To'], parsed['Subject'], parsed.get_payload())
    else:
        raise TypeError("Multipart Payload in Plain Parser. Please use multipart_eml_parsing")
        


def multipart_eml_parsing(user: ZimbraUser, payload: list, dict_mail: dict) -> dict:
    #TODO correct the types, its not a list but a list of email message objects
    """Generate a dictionary of multipart-parts form a multipart email payload

        Parameters:
            parsedcontent (dict): an existing dictionary, key 'body' contains the body, key 'attachments' contains a [WebkitAttachments] list of attachments
            payload (list): list of email message objects

        Returns:
            dict: A dictionary with body and attachments
    """

    for p in payload:
        if type(p.get_payload()) == list:
            raise NotImplementedError()
            #TODO recursive handling here!

        if "attachment" not in p.get('Content-Disposition', ''):
            dict_mail['body'] = p.get_payload()

        if "attachment" in p.get('Content-Disposition', ''):
            dict_mail['attachments'].append(WebkitAttachment(
                mimetype=p.get('Content-Type')[:p.get('Content-Type').find(";")],
                filename=re.findall('filename=\"(.*?)\"', p.get('Content-Disposition'))[0],
                content=base64.b64decode(p.get_payload())
            ))

    return dict_mail