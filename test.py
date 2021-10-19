from zimbra import send_mail_as

import creds_secret
"""creds_secret.py 
USERNAME = "xxxx"
PASSWORD = "xxxx"
"""

import logging

logging.basicConfig(filename="debug.log", level=logging.DEBUG)

def main():
    send_mail_as(f"{creds_secret.USERNAME}@student.dhbw-mannheim.de", "hello, world!", "hello from python!",
                 username=creds_secret.USERNAME, password=creds_secret.PASSWORD)


if __name__ == "__main__":
    main()
