from typing import List, Dict, Union, Any
from email.parser import Parser

import zimbraweb


class UnsupportedEMLError(Exception):
    """Exception for unsupported EML"""
    pass


class MissingHeadersError(UnsupportedEMLError):
    """Exception for missing headers"""
    pass


class ContentTypeNotSupportedError(UnsupportedEMLError):
    """Exception for unsupported content types"""
    pass


def parse_eml(eml: str) -> Dict[str, Union[str, List[Any]]]:
    """Generate a dictionary for generate_payload() from an EML file.

    Args:
        eml (str): The EML string to parse.

    Returns:
        Dict[str, Union[str, List[WebkitAttachment]]]: A dictionary of the parsed EML file.
    """
    parsed = Parser().parsestr(eml)
    out = {}
    for header_name, header_value in parsed.items():
        out[header_name.lower()] = header_value.replace("\n", "").replace("\r", "")
    if "to" not in out:
        raise MissingHeadersError("Missing 'To' header")
    if "subject" not in out:
        raise MissingHeadersError("Missing 'Subject' header")

    ct = parsed.get_content_type()
    if ct == "text/plain":
        out["body"] = parsed.get_payload(decode=True).decode(parsed.get_content_charset())
    elif ct == "multipart/mixed":
        out["attachments"] = []
        for part in parsed.get_payload():
            if part.get_content_disposition() == "attachment":
                out["attachments"].append(zimbraweb.WebkitAttachment(
                    mimetype=part.get_content_type(),
                    filename=part.get_filename(),
                    content=part.get_payload(decode=True)
                ))
            else:
                if part.get_content_type() == "text/plain":
                    if "body" in out:  # we already have a body
                        raise UnsupportedEMLError("EML contains more than one plaintext body")
                    out["body"] = part.get_payload(decode=True).decode(part.get_content_charset())
                else:
                    raise UnsupportedEMLError(f"EML contains unsupported content type: {part.get_content_type()}")
        if "body" not in out:
            out["body"] = ""
    else:
        raise ContentTypeNotSupportedError(f"Content-Type: {ct} not supported")

    return out


def is_parsable(eml: str) -> bool:
    """Check eml string for parsability

    Args:
        eml (str): The EML string to parse.

    Returns:
        bool if parse_eml() will throw an error.
    """

    try:
        parse_eml(eml)
        return True
    except UnsupportedEMLError:
        return False
