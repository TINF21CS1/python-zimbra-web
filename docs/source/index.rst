.. Python Zimbra Web documentation master file, created by
   sphinx-quickstart on Fri Oct 29 19:04:26 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Python Zimbra Web's documentation!
=============================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`



Contents
--------

.. toctree::
   zimbraweb

Usage
-----

You can use :meth:`zimbraweb.ZimbraUser` to send E-mails. You can send multiple
E-mails within a single session.

.. code:: python

   from zimbraweb import ZimbraUser

   user = ZimbraUser("https://myzimbra.server")
   user.login("s000000", "hunter2")
   user.send_mail(to="receiver@example.com", subject="subject", body="body", cc="cc@example.com")
   user.logout()

Sending EMLs
~~~~~~~~~~~~

Please note the `Limitations <#known-limitations>`__ when trying to
parse EML.

.. code:: python

   from zimbraweb import ZimbraUser

   user = ZimbraUser("https://myzimbra.server")
   user.login("s000000", "hunter2")
   emlstr = open("myemlfile.eml").read()
   user.send_eml(emlstr)

Sending raw WebkitPayloads
~~~~~~~~~~~~~~~~~~~~~~~~~~

If you don’t want to rely on us to generate the payload, you can
generate a payload yourself and send it using :meth:`zimbraweb.ZimbraUser.send_raw_payload`.

.. code:: python

   from zimbraweb import ZimbraUser

   user = ZimbraUser("https://myzimbra.server")
   user.login("s000000", "hunter2")

   # you could also generate the payload yourself or use our library
   raw_payload, boundary = user.generate_webkit_payload(to="to@example.com", subject="hello world!", body="this is a raw payload.") 

   # then send the raw_payload bytes
   user.send_raw_payload(raw_payload, boundary)

   user.logout()

Attachments
~~~~~~~~~~~

You can generate attachments using the :meth:`zimbraweb.WebkitAttachment` class:

.. code:: python

   from zimbraweb import ZimbraUser, WebkitAttachment

   user = ZimbraUser("https://myzimbra.server")
   user.login("s000000", "hunter2")

   attachments = []
   with open("myfile.jpg", "rb") as f:
      attachments.append(WebkitAttachment(content=f.read(), filename="attachment.jpg"))

   user.send_mail(to="receiver@example.com", subject="subject", body="body", attachments=attachments)
   user.logout()

Known Limitations
-----------------

-  Emoji is not supported, even though other UTF-8 characters are. See
   Issue #3
-  This package is made with German UIs in mind. If your UI is in a
   different language, feel free to fork and adjust the
   language-specific strings as needed. `Issue
   #43 <https://github.com/cirosec-studis/python-zimbra-web/issues/43>`__
-  The EML parsing can strictly only parse plaintext emails, optionally
   with attachments. Any emails with a Content-Type other than
   ``text/plain`` or ``multipart/mixed`` will be rejected. This is
   because the zimbra web interface does not allow HTML emails. Parsing
   ``multipart/mixed`` will only succeed if there is exactly one
   ``text/plain`` part and, optionally, attachments with the
   ``Content-Disposition: attachment`` header. If there are any
   ``multipart/alternative`` parts, the parsing will fail because we
   cannot deliver them to the Zimbra web interface.