"""
Gmail CLI for the masters repo. Uses google_auth.py for credentials.

Usage:
  python scripts/gmail_cli.py search "is:unread" [--account personal|stoop] [--limit N]
  python scripts/gmail_cli.py read <message_id> [--account ...]
  python scripts/gmail_cli.py send --to a@b.com --subject "Hi" --body "..." [--attach file ...] [--account ...]
  python scripts/gmail_cli.py draft --to a@b.com --subject "Hi" --body "..." [--attach file ...] [--account ...]

--to accepts a comma-separated list. --attach may be repeated to attach multiple files.
Default account: personal. Requires a personal Gmail token with read+send scope
(create it once: python scripts/google_auth.py consent --account personal --capability gmail).
"""
import sys, io, os, base64, argparse, mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from google_auth import service  # noqa: E402


def header(msg, name):
    for h in msg.get('payload', {}).get('headers', []):
        if h['name'].lower() == name.lower():
            return h['value']
    return ''


def search(gmail, query, limit):
    res = gmail.users().messages().list(userId='me', q=query, maxResults=limit).execute()
    ids = [m['id'] for m in res.get('messages', [])]
    print(f"\n{len(ids)} message(s) for: {query}\n")
    for mid in ids:
        m = gmail.users().messages().get(
            userId='me', id=mid, format='metadata',
            metadataHeaders=['From', 'Subject', 'Date']).execute()
        print(f"  {header(m,'Date')[:25]:25s}  {header(m,'From')[:30]:30s}")
        print(f"    {header(m,'Subject')}")
        print(f"    id: {mid}\n")


def read(gmail, mid):
    m = gmail.users().messages().get(userId='me', id=mid, format='full').execute()
    print(f"From:    {header(m,'From')}")
    print(f"To:      {header(m,'To')}")
    print(f"Subject: {header(m,'Subject')}")
    print(f"Date:    {header(m,'Date')}\n{'-'*60}")

    def walk(part):
        if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
            return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', 'replace')
        for sub in part.get('parts', []):
            t = walk(sub)
            if t:
                return t
        return ''
    body = walk(m['payload']) or m.get('snippet', '')
    print(body)


def build_raw(to, subject, body, sender=None, attachments=None):
    attachments = attachments or []
    if attachments:
        mime = MIMEMultipart()
        mime.attach(MIMEText(body))
        for path in attachments:
            if not os.path.isfile(path):
                raise SystemExit(f"ERROR: attachment not found: {path}")
            ctype, _ = mimetypes.guess_type(path)
            maintype, subtype = (ctype or 'application/octet-stream').split('/', 1)
            with open(path, 'rb') as fh:
                part = MIMEBase(maintype, subtype)
                part.set_payload(fh.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(path))
            mime.attach(part)
    else:
        mime = MIMEText(body)
    mime['To'] = to
    mime['Subject'] = subject
    if sender:
        mime['From'] = sender
    return base64.urlsafe_b64encode(mime.as_bytes()).decode()


def send(gmail, to, subject, body, attachments=None):
    sent = gmail.users().messages().send(
        userId='me', body={'raw': build_raw(to, subject, body, attachments=attachments)}).execute()
    print(f"Sent. id={sent.get('id')}  to={to}  attachments={len(attachments or [])}")


def draft(gmail, to, subject, body, attachments=None):
    # NOTE: drafts().create needs the gmail.compose scope, which the default
    # read+send token does NOT include. Re-consent with compose to enable drafts:
    #   python scripts/google_auth.py consent --account <acct> --capability gmail
    # (after adding gmail.compose to SCOPES['gmail'] in google_auth.py).
    # Sending works without it — use `send` if you just need to deliver mail.
    d = gmail.users().drafts().create(
        userId='me',
        body={'message': {'raw': build_raw(to, subject, body, attachments=attachments)}}).execute()
    print(f"Draft created. id={d.get('id')} (nothing was sent)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--account', default='personal', choices=['personal', 'stoop'])
    sub = p.add_subparsers(dest='cmd')

    sp = sub.add_parser('search'); sp.add_argument('query'); sp.add_argument('--limit', type=int, default=10)
    rp = sub.add_parser('read'); rp.add_argument('message_id')
    for name in ('send', 'draft'):
        xp = sub.add_parser(name)
        xp.add_argument('--to', required=True, help='comma-separated recipient list')
        xp.add_argument('--subject', required=True)
        xp.add_argument('--body', required=True)
        xp.add_argument('--attach', action='append', default=[], help='file path; repeatable')

    args = p.parse_args()
    if not args.cmd:
        p.print_help(); sys.exit(1)

    gmail = service(args.account, 'gmail', 'gmail', 'v1')
    if args.cmd == 'search':
        search(gmail, args.query, args.limit)
    elif args.cmd == 'read':
        read(gmail, args.message_id)
    elif args.cmd == 'send':
        send(gmail, args.to, args.subject, args.body, args.attach)
    elif args.cmd == 'draft':
        draft(gmail, args.to, args.subject, args.body, args.attach)


if __name__ == '__main__':
    main()
