"""
SMS reader for the masters repo. Reads SMS Backup & Restore XML backups from
Google Drive (personal account). Uses google_auth.py for credentials.

Phone side: the "SMS Backup & Restore" app (SyncTech) uploads sms-*.xml files
to Drive on a schedule. This CLI finds the newest one, caches it locally in
.secrets/sms/ (gitignored - texts must never be committed), and parses it.

Usage:
  python scripts/sms_cli.py sync                      # download newest backup from Drive
  python scripts/sms_cli.py recent [--limit N]        # latest messages
  python scripts/sms_cli.py search "text" [--contact NAME] [--limit N]
  python scripts/sms_cli.py thread <name-or-number> [--limit N]
  python scripts/sms_cli.py contacts                  # who you text, with counts

Note: covers SMS and MMS only. RCS "chat features" conversations in Google
Messages live in a private database the backup app cannot read.
"""
import sys, io, os, re, glob, zipfile, argparse
import xml.etree.ElementTree as ET
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(REPO, '.secrets', 'sms')
BACKUP_NAME = re.compile(r'^sms-\d+\.xml(\.zip)?$', re.IGNORECASE)


def sync(account='personal'):
    from google_auth import service
    from googleapiclient.http import MediaIoBaseDownload
    drive = service(account, 'drive', 'drive', 'v3')
    files = drive.files().list(
        q="name contains 'sms-' and trashed = false",
        pageSize=25, orderBy='modifiedTime desc',
        fields='files(id,name,size,modifiedTime)',
    ).execute().get('files', [])
    backups = [f for f in files if BACKUP_NAME.match(f.get('name', ''))]
    if not backups:
        print("No sms-*.xml backups found in Drive yet.")
        print("On the phone: SMS Backup & Restore > Set up a backup > Google Drive,")
        print("signed in as keith.dumanski@gmail.com. Then run a manual 'Back up now'.")
        sys.exit(1)
    newest = backups[0]
    os.makedirs(CACHE_DIR, exist_ok=True)
    dest = os.path.join(CACHE_DIR, newest['name'])
    if not os.path.exists(dest):
        with open(dest, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, drive.files().get_media(fileId=newest['id']))
            done = False
            while not done:
                _, done = downloader.next_chunk()
    if dest.lower().endswith('.zip'):
        with zipfile.ZipFile(dest) as z:
            inner = next(n for n in z.namelist() if n.lower().endswith('.xml'))
            z.extract(inner, CACHE_DIR)
            dest = os.path.join(CACHE_DIR, inner)
    msgs = parse(dest)
    # keep only the newest xml so the cache doesn't grow unbounded
    for old in glob.glob(os.path.join(CACHE_DIR, 'sms-*')):
        if os.path.abspath(old) != os.path.abspath(dest):
            os.remove(old)
    print(f"Synced {newest['name']} ({int(newest.get('size', 0)) // 1024} KB, "
          f"backup dated {newest['modifiedTime'][:16].replace('T', ' ')})")
    print(f"{len(msgs)} messages, "
          f"{msgs[0]['dt']:%Y-%m-%d} to {msgs[-1]['dt']:%Y-%m-%d}" if msgs else "0 messages")


def latest_cached():
    xmls = glob.glob(os.path.join(CACHE_DIR, 'sms-*.xml'))
    if not xmls:
        print("No cached backup. Run:  python scripts/sms_cli.py sync")
        sys.exit(1)
    return max(xmls, key=os.path.getmtime)


def parse(path):
    """Yield dicts: dt, direction ('recv'/'sent'), address, contact, body."""
    msgs = []
    for _, el in ET.iterparse(path, events=('end',)):
        if el.tag == 'sms':
            box = el.get('type')
            body = el.get('body') or ''
        elif el.tag == 'mms':
            box = el.get('msg_box')
            body = ' '.join(
                p.get('text') for p in el.iter('part')
                if p.get('ct') == 'text/plain' and p.get('text')
            )
        else:
            continue
        try:
            dt = datetime.fromtimestamp(int(el.get('date', '0')) / 1000)
        except (ValueError, OSError):
            dt = datetime(1970, 1, 1)
        contact = el.get('contact_name') or ''
        if contact in ('(Unknown)', 'null'):
            contact = ''
        msgs.append({
            'dt': dt,
            'direction': 'sent' if box == '2' else 'recv',
            'address': el.get('address') or '',
            'contact': contact,
            'body': body.strip(),
        })
        el.clear()
    msgs.sort(key=lambda m: m['dt'])
    return msgs


def digits(s):
    d = re.sub(r'\D', '', s or '')
    return d[-10:] if len(d) >= 10 else d


def matches_contact(m, who):
    w = who.lower()
    return (w in m['contact'].lower()) or (digits(who) and digits(who) == digits(m['address']))


def label(m):
    who = m['contact'] or m['address'] or '?'
    arrow = '->' if m['direction'] == 'sent' else '<-'
    return f"{m['dt']:%Y-%m-%d %H:%M} {arrow} {who}"


def show(msgs):
    if not msgs:
        print("No messages matched.")
        return
    for m in msgs:
        body = m['body'] or '[no text / media only]'
        print(f"{label(m)}: {body}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--account', default='personal')
    sub = p.add_subparsers(dest='cmd')

    sub.add_parser('sync')

    rp = sub.add_parser('recent')
    rp.add_argument('--limit', type=int, default=30)

    sp = sub.add_parser('search')
    sp.add_argument('query')
    sp.add_argument('--contact')
    sp.add_argument('--limit', type=int, default=50)

    tp = sub.add_parser('thread')
    tp.add_argument('who')
    tp.add_argument('--limit', type=int, default=50)

    sub.add_parser('contacts')

    args = p.parse_args()
    if not args.cmd:
        p.print_help(); sys.exit(1)

    if args.cmd == 'sync':
        sync(args.account)
        return

    msgs = parse(latest_cached())

    if args.cmd == 'recent':
        show(msgs[-args.limit:])
    elif args.cmd == 'search':
        hits = [m for m in msgs if args.query.lower() in m['body'].lower()]
        if args.contact:
            hits = [m for m in hits if matches_contact(m, args.contact)]
        show(hits[-args.limit:])
    elif args.cmd == 'thread':
        show([m for m in msgs if matches_contact(m, args.who)][-args.limit:])
    elif args.cmd == 'contacts':
        counts = {}
        for m in msgs:
            key = m['contact'] or m['address'] or '?'
            counts[key] = counts.get(key, 0) + 1
        for who, n in sorted(counts.items(), key=lambda kv: -kv[1]):
            print(f"  {n:5d}  {who}")


if __name__ == '__main__':
    main()
