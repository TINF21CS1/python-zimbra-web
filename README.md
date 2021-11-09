# Python Zimbra Web
| branch    | status           |
|-----------|------------------|
| main      | [![Tests](https://github.com/cirosec-studis/python-zimbra-web/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/cirosec-studis/python-zimbra-web/actions/workflows/tests.yml) | 
| develop   | [![Tests](https://github.com/cirosec-studis/python-zimbra-web/actions/workflows/tests.yml/badge.svg?branch=develop)](https://github.com/cirosec-studis/python-zimbra-web/actions/workflows/tests.yml) |

## Usage

For the entire documentation please see [https://cirosec-studis.github.io/python-zimbra-web](https://cirosec-studis.github.io/python-zimbra-web]).

The documentation for the develop branch can be found here: [https://cirosec-studis.github.io/python-zimbra-web/develop/](https://cirosec-studis.github.io/python-zimbra-web/develop)

You can use `ZimbraUser` to send E-mails. You can send multiple E-mails within a single session.

```python
from zimbraweb import ZimbraUser

user = ZimbraUser("https://myzimbra.server")
user.login("s000000", "hunter2")
user.send_mail(to="receiver@example.com", subject="subject", body="body", cc="cc@example.com")
user.logout()
```

### Sending raw WebkitPayloads

If you don't want to rely on us to generate the payload, you can generate a payload yourself and send it using

```python
from zimbraweb import ZimbraUser

user = ZimbraUser("https://myzimbra.server")
user.login("s000000", "hunter2")

# you could also generate the payload yourself or use our library
raw_payload, boundary = user.generate_webkit_payload(to="to@example.com", subject="hello world!", body="this is a raw payload.") 

# then send the raw_payload bytes
user.send_raw_payload(raw_payload, boundary)

user.logout()
```


### Attachments

You can generate attachments using the `WebkitAttachment` class:

```python
from zimbraweb import ZimbraUser, WebkitAttachment

user = ZimbraUser("https://myzimbra.server")
user.login("s000000", "hunter2")

attachments = []
with open("myfile.jpg", "rb") as f:
   attachments.append(WebkitAttachment(content=f.read(), filename="attachment.jpg"))

user.send_mail(to="receiver@example.com", subject="subject", body="body", attachments=attachments)
user.logout()
```

## Known Limitations

* Emoji is not supported, even though other UTF-8 characters are. See Issue #3
* This package is made with German UIs in mind. If your UI is in a different language, feel free to fork and adjust the language-specific strings as needed. [Issue #43](https://github.com/cirosec-studis/python-zimbra-web/issues/43)

## Install

```
pip install git+https://github.com/cirosec-studis/python-zimbra-web/
```

## Contributing

1. Best practice is to develop in a python3.8 virtual env: `python3.8 -m venv env`, `source env/bin/activate` (Unix) or `env\Scripts\activate.ps1` (Windows)
2. Install dev-requirements `pip install -r requirements_dev.txt`
3. When working on a new feature, checkout to `git branch -b feature_myfeaturename`. We are using [this branching model](https://nvie.com/posts/a-successful-git-branching-model/)
4. Before committing, check 
   1. `mypy src` returns no failures.
   2. `flake8 src tests` returns no problems.
   3. `pytest` has no unexpected failed tests.
   4. Optionoally, test with `tox`. Might take a few minutes so maybe only run before push.

### Development Install

```python
pip install -e .
```

This installs the package with symlink, so the package is automatically updated, when files are changed.
It can then be called in a python console.
