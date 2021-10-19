# Python Zimbra

## Usage

```python
from zimbra import ZimbraUser

user = ZimbraUser()
user.login("s000000", "hunter2")
user.send_mail("receiver@example.com", "subject", "body")
```
