"""
Google Drive CLI for the masters repo. Uses google_auth.py for credentials.

Usage:
  python scripts/drive_cli.py recent [--account personal|stoop] [--limit N]
  python scripts/drive_cli.py search "query" [--type doc|sheet|slide|pdf|folder] [--recent DAYS]
  python scripts/drive_cli.py read <file_id>

Default account: personal (its token already works).
"""
import sys, io, os, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from google_auth import service  # noqa: E402

MIME = {
    'doc': 'application/vnd.google-apps.document',
    'sheet': 'application/vnd.google-apps.spreadsheet',
    'slide': 'application/vnd.google-apps.presentation',
    'pdf': 'application/pdf',
    'folder': 'application/vnd.google-apps.folder',
}
FRIENDLY = {v: k.capitalize() for k, v in MIME.items()}


def search(drive, query=None, ftype=None, recent_days=None, limit=20):
    parts = []
    if query:
        parts.append(f"fullText contains '{query}'")
    if ftype in MIME:
        parts.append(f"mimeType = '{MIME[ftype]}'")
    if recent_days:
        from datetime import datetime, timedelta
        cutoff = (datetime.utcnow() - timedelta(days=recent_days)).strftime('%Y-%m-%dT%H:%M:%S')
        parts.append(f"modifiedTime > '{cutoff}'")
    parts.append("trashed = false")
    return drive.files().list(
        q=' and '.join(parts), pageSize=limit,
        fields='files(id,name,mimeType,modifiedTime,webViewLink)',
        orderBy='modifiedTime desc',
    ).execute().get('files', [])


def show(files):
    if not files:
        print("No files found.")
        return
    print(f"\n{len(files)} file(s):\n")
    for f in files:
        kind = FRIENDLY.get(f.get('mimeType', ''), f.get('mimeType', '').split('/')[-1][:10])
        print(f"  [{kind:7s}] {f.get('modifiedTime','')[:10]}  {f.get('name','Untitled')}")
        print(f"            id: {f.get('id','')}")
        if f.get('webViewLink'):
            print(f"            {f['webViewLink']}")
        print()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--account', default='personal', choices=['personal', 'stoop'])
    sub = p.add_subparsers(dest='cmd')

    sp = sub.add_parser('search')
    sp.add_argument('query')
    sp.add_argument('--type', choices=list(MIME) + ['any'], default='any')
    sp.add_argument('--recent', type=int)
    sp.add_argument('--limit', type=int, default=20)

    rp = sub.add_parser('recent')
    rp.add_argument('--limit', type=int, default=20)
    rp.add_argument('--type', choices=list(MIME) + ['any'], default='any')

    dp = sub.add_parser('read')
    dp.add_argument('file_id')

    args = p.parse_args()
    if not args.cmd:
        p.print_help(); sys.exit(1)

    drive = service(args.account, 'drive', 'drive', 'v3')

    if args.cmd == 'search':
        show(search(drive, args.query, None if args.type == 'any' else args.type, args.recent, args.limit))
    elif args.cmd == 'recent':
        show(search(drive, None, None if args.type == 'any' else args.type, None, args.limit))
    elif args.cmd == 'read':
        meta = drive.files().get(fileId=args.file_id, fields='id,name,mimeType').execute()
        mime = meta.get('mimeType', '')
        print(f"\n{'='*60}\n  {meta.get('name','Untitled')}\n{'='*60}\n")
        if mime == 'application/vnd.google-apps.document':
            docs = service(args.account, 'drive', 'docs', 'v1')
            doc = docs.documents().get(documentId=args.file_id).execute()
            out = []
            for el in doc['body']['content']:
                for run in el.get('paragraph', {}).get('elements', []):
                    if 'textRun' in run:
                        out.append(run['textRun']['content'])
            print(''.join(out))
        elif mime == 'application/vnd.google-apps.spreadsheet':
            print(drive.files().export(fileId=args.file_id, mimeType='text/csv').execute().decode('utf-8'))
        else:
            try:
                print(drive.files().export(fileId=args.file_id, mimeType='text/plain').execute().decode('utf-8'))
            except Exception:
                print(f"[Cannot export {mime}. Open in browser.]")


if __name__ == '__main__':
    main()
