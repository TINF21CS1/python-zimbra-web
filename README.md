# Python Zimbra
| branch    | status           |
|-----------|------------------|
| main      | [![Tests](https://github.com/cirosec-studis/python-zimbra/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/cirosec-studis/python-zimbra/actions/workflows/tests.yml) | 
| develop   | [![Tests](https://github.com/cirosec-studis/python-zimbra/actions/workflows/tests.yml/badge.svg?branch=develop)](https://github.com/cirosec-studis/python-zimbra/actions/workflows/tests.yml) |

## Usage

```python
from zimbra import ZimbraUser

user = ZimbraUser("https://myzimbra.server")
user.login("s000000", "hunter2")
user.send_mail(from_header="Me <me@myzimbra.server>", to="receiver@example.com", subject="subject", body="body")
```

## Known Limitations

* Emoji is not supported, even though other UTF-8 characters are. See Issue #3

## Contributing

1. Best practice is to develop in a python3.8 virtual env: `python3.8 -m venv env`, `source env/bin/activate` (Unix) or `env\Scripts\activate.ps1` (Windows)
2. Install dev-requirements `pip install -r requirements_dev.txt`
3. When working on a new feature, checkout to `git branch -b feature_myfeaturename`. We are using [this branching model](https://nvie.com/posts/a-successful-git-branching-model/)
4. Before committing, check 
   1. `mypy src` returns no failures.
   2. `flake8 src tests` returns no problems.
   3. `pytest` has no unexpected failed tests.
   4. Optionoally, test with `tox`. Might take a few minutes so maybe only run before push.

### Install

```python
pip install -e .
```

This installs the package with symlink, so the package is automatically updated, when files are changed.
It can then be called in a python console.