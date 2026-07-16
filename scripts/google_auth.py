"""
Reusable Google OAuth helper for the masters repo.

Modeled on front-end/scripts/drive_search.py (the proven pattern): load a saved
OAuth token, auto-refresh it, and only fall back to an interactive consent flow
when no valid token exists. Multi-account aware — each account+capability has its
own token file under .secrets/.

Tokens and the OAuth client (credentials.json) live in masters/.secrets/, which is
gitignored. Nothing here ever gets committed.
"""
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SECRETS_DIR = os.path.join(SCRIPT_DIR, '..', '.secrets')

# The OAuth "client" file (installed-app type). Needed only when a token is
# missing/unrefreshable and we must run a fresh consent flow.
CLIENT_FILE = os.path.join(SECRETS_DIR, 'credentials.json')

# Per-account, per-capability token files. Drive/Gmail are separate OAuth grants
# because Google issues one refresh token per scope-set per consent.
TOKENS = {
    ('personal', 'drive'): 'personal_drive_token.json',
    ('personal', 'gmail'): 'personal_gmail_token.json',
    ('personal', 'photos'): 'personal_photos_token.json',
    ('stoop',    'drive'): 'stoop_drive_token.json',
    ('stoop',    'gmail'): 'stoop_gmail_token.json',
    ('stoop',    'photos'): 'stoop_photos_token.json',
    # St. Mark's Yoga brand account (12stmarksyoga@gmail.com) - used by the daily
    # insights pipeline to drop the raw Recess CSV exports into the studio's Drive.
    ('stmarksyoga', 'drive'): 'stmarksyoga_drive_token.json',
}

SCOPES = {
    # Broad 'drive' scope already covers reading/exporting Docs, Sheets, Slides.
    # Keep it to exactly what existing tokens were granted so they load as-is.
    'drive': [
        'https://www.googleapis.com/auth/drive',
    ],
    # Full Gmail read + send. readonly alone can't send; send alone can't read.
    'gmail': [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
    ],
    # Google Photos Picker API (read-only). Google removed the old full-library
    # read scopes in March 2025; this is the supported replacement. The user
    # picks specific items in a Google-hosted picker and we only ever receive
    # exactly what they select — there is no "browse the whole library" anymore.
    'photos': [
        'https://www.googleapis.com/auth/photospicker.mediaitems.readonly',
    ],
}


def token_path(account, capability):
    name = TOKENS.get((account, capability))
    if not name:
        raise ValueError(f"Unknown account/capability: {account}/{capability}")
    return os.path.join(SECRETS_DIR, name)


def get_credentials(account, capability, allow_consent=True):
    """
    Return valid Google credentials for (account, capability).

    Order: load saved token -> refresh if expired -> (optional) interactive
    consent if no usable token. Refreshed tokens are written back so the next
    call is non-interactive.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    tok = token_path(account, capability)
    scopes = SCOPES[capability]

    # CI path: no .secrets/ on a GitHub Actions runner, so allow the token JSON to
    # arrive as an env var (e.g. GOOGLE_TOKEN_PERSONAL_DRIVE from a repo secret).
    # Local runs still use the file, which stays the source of truth.
    env_var = f'GOOGLE_TOKEN_{account.upper()}_{capability.upper()}'
    raw = os.environ.get(env_var)
    if raw and not os.path.exists(tok):
        import json as _json
        info = _json.loads(raw)
        creds = Credentials.from_authorized_user_info(info, scopes)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())  # refreshed in-memory; runner is ephemeral
        if creds and creds.valid:
            return creds
        raise RuntimeError(f'{env_var} was set but did not yield valid credentials.')

    if os.path.exists(tok):
        try:
            creds = Credentials.from_authorized_user_file(tok, scopes)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(tok, 'w') as f:
                    f.write(creds.to_json())
            if creds and creds.valid:
                return creds
        except Exception:
            pass  # fall through to consent

    if not allow_consent:
        raise RuntimeError(
            f"No valid token for {account}/{capability} at {tok}. "
            f"Run: python scripts/google_auth.py consent --account {account} --capability {capability}"
        )

    # Interactive consent — requires a human at a browser. Sign in as the
    # intended account when the Google page opens.
    from google_auth_oauthlib.flow import InstalledAppFlow
    if not os.path.exists(CLIENT_FILE):
        raise RuntimeError(f"OAuth client file missing: {CLIENT_FILE}")
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_FILE, scopes)
    creds = flow.run_local_server(port=8765)
    with open(tok, 'w') as f:
        f.write(creds.to_json())
    return creds


def service(account, capability, api, version, allow_consent=False):
    """Build a googleapiclient service. Defaults to non-interactive."""
    from googleapiclient.discovery import build
    creds = get_credentials(account, capability, allow_consent=allow_consent)
    return build(api, version, credentials=creds)


if __name__ == '__main__':
    import sys, io, argparse
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    p = argparse.ArgumentParser(description='Google auth helper')
    sub = p.add_subparsers(dest='cmd')

    c = sub.add_parser('consent', help='Run interactive OAuth consent for one account+capability')
    c.add_argument('--account', required=True, choices=['personal', 'stoop', 'stmarksyoga'])
    c.add_argument('--capability', required=True, choices=['drive', 'gmail', 'photos'])

    s = sub.add_parser('status', help='Show which tokens exist and are valid')

    args = p.parse_args()

    if args.cmd == 'consent':
        print(f"Opening Google consent for {args.account}/{args.capability} ...")
        print(f"  -> Sign in as the {args.account.upper()} account when the browser opens.")
        get_credentials(args.account, args.capability, allow_consent=True)
        print(f"Saved token: {token_path(args.account, args.capability)}")

    elif args.cmd == 'status':
        for (acct, cap), name in TOKENS.items():
            path = os.path.join(SECRETS_DIR, name)
            if not os.path.exists(path):
                print(f"  {acct:8s} {cap:6s}: (no token)")
                continue
            try:
                creds = get_credentials(acct, cap, allow_consent=False)
                who = ''
                if cap == 'drive':
                    svc = service(acct, cap, 'drive', 'v3')
                    who = svc.about().get(fields='user(emailAddress)').execute()['user']['emailAddress']
                elif cap == 'gmail':
                    try:
                        svc = service(acct, cap, 'gmail', 'v1')
                        who = svc.users().getProfile(userId='me').execute().get('emailAddress', '')
                    except Exception:
                        who = '(send-only token, cannot read profile)'
                else:
                    # Photos Picker tokens have no identity/profile endpoint;
                    # a loadable, unexpired token is the only validity signal.
                    who = '(photos picker token)'
                print(f"  {acct:8s} {cap:6s}: VALID -> {who}")
            except Exception as e:
                print(f"  {acct:8s} {cap:6s}: INVALID -> {type(e).__name__}: {str(e)[:80]}")
    else:
        p.print_help()
