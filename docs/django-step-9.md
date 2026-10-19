# Django lesson 9: create a local test rider

Run this command in a local PowerShell window after database migrations:

```powershell
.\.pothholevenv\Scripts\python.exe manage.py create_rider
```

It asks for a username and a password without showing the password. Django's configured validators require at least 12 characters and reject common, numeric-only or username-like passwords. The command creates a **non-admin** account and one API token in a single database transaction. It prints the token once to your local terminal. Copy it into a private development client; never paste it into Git, chat, logs or screenshots.

The command uses `validate_password()` before `set_password()`. `set_password()` hashes the password; the database does not store its readable form. `user.full_clean()` checks the username and duplicate-account rules. `Token.objects.create()` creates the credential that Django REST Framework will recognize in an `Authorization: Token ...` header. A duplicate username or weak password stops the command without creating an account.

This is local test setup, not public self-registration. The basic DRF token has no built-in expiry. Before phone use, configure trusted HTTPS and a suitable token lifecycle; do not send a token over plain network HTTP. The local server is restricted to `127.0.0.1`.

The isolated automated tests confirmed that the account is not staff or superuser, its password is hashed, the password is never echoed by the command, and weak passwords are rejected. They did not create a real rider account in your PostgreSQL database.
