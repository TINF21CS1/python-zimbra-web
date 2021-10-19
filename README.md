# Python Zimbra

## Usage

```python
from zimbra import ZimbraUser

user = ZimbraUser()
user.login("s000000", "hunter2")
user.send_mail("receiver@example.com", "subject", "body")
```

## Tests

Main: [![Tests](https://github.com/cirosec-studis/python-zimbra/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/cirosec-studis/python-zimbra/actions/workflows/tests.yml)


Develop: [![Tests](https://github.com/cirosec-studis/python-zimbra/actions/workflows/tests.yml/badge.svg?branch=develop)](https://github.com/cirosec-studis/python-zimbra/actions/workflows/tests.yml)

