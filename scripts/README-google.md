# Google access from the masters repo

Gmail + Google Drive access, modeled on the proven `front-end/scripts/drive_search.py`
pattern: saved OAuth tokens consumed by Python scripts, auto-refreshed, never committed.

## Layout

- `scripts/google_auth.py` — shared credential helper (load token → refresh → consent fallback).
- `scripts/drive_cli.py` — Drive search/read/recent.
- `scripts/gmail_cli.py` — Gmail search/read/send/draft.
- `.secrets/` — tokens + OAuth client (`credentials.json`). **Gitignored.** Never commit.

Each account+capability has its own token file in `.secrets/`:
`personal_drive_token.json`, `personal_gmail_token.json`, `stoop_drive_token.json`, `stoop_gmail_token.json`.

## Current status

| Account | Drive | Gmail |
|---|---|---|
| personal (`keith.dumanski@gmail.com`) | ✅ working | needs one consent (read+send) |
| stoop (`keith@thestoop.ai`) | also via Claude connector | also via Claude connector |

Check anytime:

```bash
python scripts/google_auth.py status
```

## Adding / re-authorizing an account (the only step needing a browser)

```bash
# Sign in as the intended account when the browser opens.
python scripts/google_auth.py consent --account personal --capability gmail
python scripts/google_auth.py consent --account stoop    --capability gmail
python scripts/google_auth.py consent --account stoop    --capability drive
```

Each opens a Google consent page on `http://localhost:8765`, then saves the token.
The `gmail` capability requests `gmail.readonly` + `gmail.send` (full read + send).

## Usage

```bash
# Drive (personal works now)
python scripts/drive_cli.py recent --limit 10
python scripts/drive_cli.py search "lease" --type doc
python scripts/drive_cli.py read <file_id>

# Gmail (after consent)
python scripts/gmail_cli.py search "is:unread" --limit 10
python scripts/gmail_cli.py read <message_id>
python scripts/gmail_cli.py draft --to a@b.com --subject "Hi" --body "test"   # safe, sends nothing
python scripts/gmail_cli.py send  --to a@b.com --subject "Hi" --body "test"

# pick the account with --account personal|stoop (default: personal)
```

## Notes

- Tokens carry standing access (refresh tokens). Anyone with `.secrets/` can act as the account — keep it local.
- The OAuth client (`credentials.json`) is copied from `etls/`. If consent fails with an "client" error, that client may need its redirect/localhost settings checked in Google Cloud.
