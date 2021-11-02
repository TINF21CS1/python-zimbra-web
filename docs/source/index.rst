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
   zimbra

Usage
-----

You can use :meth:`zimbra.ZimbraUser` to send E-mails. You can send multiple
E-mails within a single session.

.. code:: python

   from zimbra import ZimbraUser

   user = ZimbraUser("https://myzimbra.server")
   user.login("s000000", "hunter2")
   user.send_mail(to="receiver@example.com", subject="subject", body="body", cc="cc@example.com")
   user.logout()

Sending raw WebkitPayloads
~~~~~~~~~~~~~~~~~~~~~~~~~~

If you don’t want to rely on us to generate the payload, you can
generate a payload yourself and send it using :meth:`zimbra.ZimbraUser.send_raw_payload`.

.. code:: python

   from zimbra import ZimbraUser

   user = ZimbraUser("https://myzimbra.server")
   user.login("s000000", "hunter2")

   # you could also generate the payload yourself or use our library
   raw_payload, boundary = user.generate_webkit_payload(to="to@example.com", subject="hello world!", body="this is a raw payload.") 

   # then send the raw_payload bytes
   user.send_raw_payload(raw_payload, boundary)

   user.logout()

Attachments
~~~~~~~~~~~

You can generate attachments using the :meth:`zimbra.WebkitAttachment` class:

.. code:: python

   from zimbra import ZimbraUser, WebkitAttachment

   user = ZimbraUser("https://myzimbra.server")
   user.login("s000000", "hunter2")

   attachments = []
   with open("myfile.jpg", "rb") as f:
      attachments.append(WebkitAttachment(content=f.read(), filename="attachment.jpg"))

   user.send_mail(to="receiver@example.com", subject="subject", body="body", attachments=attachments)
   user.logout()

Known Limitations
-----------------

-  Emoji is not supported, even though other UTF-8 characters are.