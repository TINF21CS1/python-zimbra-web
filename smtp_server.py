import asynchat
import base64
from email import parser
import ssl
import asyncore
import logging
import email
import email.policy

from smtpd import SMTPServer, SMTPChannel as SMTPChannel, DEBUGSTREAM

import zimbra

logging.getLogger().setLevel(logging.INFO)

# frei nach https://gist.github.com/amirasaran/510385ed6ac93f9d9ad6bdf3bcb72fc5

def decode_b64(data):
    """Wrapper for b64decode, without having to struggle with bytestrings."""
    byte_string = data.encode('utf-8')
    decoded = base64.b64decode(byte_string)
    return decoded.decode('utf-8')


def encode_b64(data):
    """Wrapper for b64encode, without having to struggle with bytestrings."""
    byte_string = data.encode('utf-8')
    encoded = base64.b64encode(byte_string)
    return encoded.decode('utf-8')


class ZimbraCredentialValidator:
    def __init__(self, username, password, smtp_server):
        self.username = username
        self.password = password
        self.channel = smtp_server
        self.session_data = zimbra.SessionData()

    def validate(self):
        if self.session_data.is_valid():
            return True
        logging.info(f"Authenticating user {self.username}")
        self.session_data = zimbra.get_session_data(self.username, self.password)
        return self.session_data.is_valid()

class ZimbraSMTPChannel(SMTPChannel):

    def __init__(self, server, conn, addr, *args, **kwargs):
        super().__init__(server, conn, addr, *args, **kwargs)
        logging.info(f"New SMTP Channel opened by {conn.getpeername()}")
        self.username = None
        self.password = None
        self.authenticated = False
        self.authenticating = False
        self.credential_instance = None

    @property
    def credential_validator(self):
        return self.smtp_server.credential_validator

    def validate_credential(self, user, password):
        self.credential_instance = self.credential_validator(user, password, self.smtp_server)
        return self.credential_instance.validate()

    def smtp_AUTH(self, arg):
        if 'PLAIN' in arg:
            split_args = arg.split(' ')
            # second arg is Base64-encoded string of blah\0username\0password
            authbits = decode_b64(split_args[1]).split('\0')
            self.username = authbits[1]
            self.password = authbits[2]
            if self.validate_credential(self.username, self.password):
                self.authenticated = True
                self.push('235 Authentication successful.')
            else:
                self.push('454 Temporary authentication failure.')
                self.close_when_done()

        elif 'LOGIN' in arg:
            self.authenticating = True
            split_args = arg.split(' ')

            # Some implmentations of 'LOGIN' seem to provide the username
            # along with the 'LOGIN' stanza, hence both situations are
            # handled.
            if len(split_args) == 2:
                self.username = decode_b64(arg.split(' ')[1])
                self.push('334 ' + encode_b64('Username'))
            else:
                self.push('334 ' + encode_b64('Username'))

        elif not self.username:
            self.username = decode_b64(arg)
            self.push('334 ' + encode_b64('Password'))
        else:
            self.authenticating = False
            self.password = decode_b64(arg)
            if self.validate_credential(self.username, self.password):
                self.authenticated = True
                self.push('235 Authentication successful.')
            else:
                self.push('454 Temporary authentication failure.')
                self.close_when_done()

    def smtp_STARTTLS(self, arg):
        if arg:
            self.push('501 Syntax error (no parameters allowed)')
        elif self.smtp_server.starttls_active and not isinstance(self.conn, ssl.SSLSocket):
            self.push('220 Ready to start TLS')
            self.conn.settimeout(30)
            self.conn = self.smtp_server.ssl_ctx.wrap_socket(self.conn, server_side=True)
            self.conn.settimeout(None)
            # re-init channel
            asynchat.async_chat.__init__(self, self.conn)
            self.line = []
            self.state = self.COMMAND
            self.seen_greeting = 0
            self.mailfrom = None
            self.rcpttos = []
            self.data = ''
            self.authenticated = False
            self.authenticating = False
            self.service_channel = False
        else:
            self.push('454 TLS not available due to temporary reason')

    def smtp_EHLO(self, arg):
        if not arg:
            self.push('501 Syntax: EHLO hostname')
            return
        # See issue #21783 for a discussion of this behavior.
        if self.seen_greeting:
            self.push('503 Duplicate HELO/EHLO')
            return
        self._set_rset_state()
        self.seen_greeting = arg
        self.extended_smtp = True
        self.push('250-%s' % self.fqdn)
        self.push('250-AUTH LOGIN PLAIN')
        if not isinstance(self.conn, ssl.SSLSocket) and self.smtp_server.starttls_active:
            self.push('250-STARTTLS')
        if self.data_size_limit:
            self.push('250-SIZE %s' % self.data_size_limit)
            self.command_size_limits['MAIL'] += 26
        if not self._decode_data:
            self.push('250-8BITMIME')
        if self.enable_SMTPUTF8:
            self.push('250-SMTPUTF8')
            self.command_size_limits['MAIL'] += 10

        self.push('250 HELP')

    # SMTP and ESMTP commands
    def smtp_HELO(self, arg):
        if not arg:
            self.push('501 Syntax: HELO hostname')
            return
        # See issue #21783 for a discussion of this behavior.
        if self.seen_greeting:
            self.push('503 Duplicate HELO/EHLO')
            return
        self._set_rset_state()
        self.seen_greeting = arg
        self.push('250 %s' % self.fqdn)

        # This code is taken directly from the underlying smtpd.SMTPChannel
        # support for AUTH is added.

    @property
    def allow_args_before_auth(self):
        return ['AUTH', 'EHLO', 'HELO', 'NOOP', 'RSET', 'STARTTLS', 'QUIT']

    def run_command_with_arg(self, command, arg):
        method = getattr(self, 'smtp_' + command, None)
        if not method or command.lower() == 'starttls' and not self.smtp_server.starttls_active:
            self.push('500 Error: command "%s" not recognized' % command)
            return

        # White list of operations that are allowed prior to AUTH.
        if command not in self.allow_args_before_auth:
            if not self.authenticated:
                self.push('530 Authentication required')
                return

        method(arg)

    def found_terminator(self):
        line = self._emptystring.join(self.received_lines)
        print('Data:', repr(line), file=DEBUGSTREAM)
        self.received_lines = []
        if self.smtp_state == self.COMMAND:
            sz, self.num_bytes = self.num_bytes, 0
            if not line:
                self.push('500 Error: bad syntax')
                return
            if not self._decode_data:
                line = str(line, 'utf-8')
            i = line.find(' ')

            if self.authenticating:
                # If we are in an authenticating state, call the
                # method smtp_AUTH.
                arg = line.strip()
                command = 'AUTH'
            elif i < 0:
                command = line.upper()
                arg = None
            else:
                command = line[:i].upper()
                arg = line[i + 1:].strip()
            max_sz = (self.command_size_limits[command]
                      if self.extended_smtp else self.command_size_limit)
            if sz > max_sz:
                self.push('500 Error: line too long')
                return

            self.run_command_with_arg(command, arg)
            return
        else:
            if self.smtp_state != self.DATA:
                self.push('451 Internal confusion')
                self.num_bytes = 0
                return
            if self.data_size_limit and self.num_bytes > self.data_size_limit:
                self.push('552 Error: Too much mail data')
                self.num_bytes = 0
                return
            # Remove extraneous carriage returns and de-transparency according
            # to RFC 5321, Section 4.5.2.
            data = []
            for text in line.split(self._linesep):
                if text and text[0] == self._dotsep:
                    data.append(text[1:])
                else:
                    data.append(text)
            self.received_data = self._newline.join(data)
            args = (self.peer, self.mailfrom, self.rcpttos, self.received_data)
            kwargs = {
                'credential_instance': self.credential_instance
            }
            if not self._decode_data:
                kwargs.update({
                    'mail_options': self.mail_options,
                    'rcpt_options': self.rcpt_options,
                })
            status = self.smtp_server.process_message(*args, **kwargs)
            self._set_post_data_state()
            if not status:
                self.push('250 OK')
            else:
                self.push(status)


class ZimbraSMTPServer(SMTPServer):
    channel_class = ZimbraSMTPChannel
    credential_validator = ZimbraCredentialValidator

    def __init__(self, localaddr, remoteaddr, cert_file=None, key_file=None):
        super().__init__(localaddr, remoteaddr)
        self.starttls_active = False
        self.ssl_ctx = None
        if key_file and cert_file:
            print("TLS support is active")
            self.starttls_active = True
            self.ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.ssl_ctx.load_cert_chain(certfile=cert_file, keyfile=key_file)

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        logging.info(f"Received message from {peer}, claiming to be {mailfrom}")

        if not "credential_instance" in kwargs:
            logging.error("Something went terribly wrong, user made request without credential_instance")
            return
        session_data = kwargs["credential_instance"].session_data
        if not session_data.is_valid():
            logging.error("Something went terribly wrong, user made request without valid session data")
            return

        mail = email.message_from_bytes(data, policy=email.policy.default)

        body = mail.get_payload()

        for rcpt in rcpttos: 
            # TODO: send 1 mail with multiple TOs instead of multiple mails. requires further reverse-engineering of the API
            zimbra.send_mail_as(rcpt, mail.get("Subject", failobj="[]"), body,
                               session_data=session_data)
            logging.info(f"Sent mail to {rcpt}")


def run():
    foo = ZimbraSMTPServer(('localhost', 25), None)
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        print("kb interrupt")


if __name__ == '__main__':
	run()
