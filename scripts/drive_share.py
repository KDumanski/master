"""
Google Drive write/share CLI for the masters repo (companion to drive_cli.py,
which is read-only). Uses google_auth.py for credentials (broad 'drive' scope,
which already permits create/upload/share).

Usage:
  # make a folder (optionally inside a parent), print its id + link
  python scripts/drive_share.py mkfolder "Stark Level — Creative" [--parent <id>]

  # upload one or more files into a folder
  python scripts/drive_share.py upload <folder_id> path/to/a.mp4 path/to/b.mp4 ...

  # share a file/folder with people (role: reader|writer|commenter)
  python scripts/drive_share.py share <file_or_folder_id> --emails a@x.com,b@y.com [--role writer] [--no-notify] [--message "..."]

  # one-shot: make folder, upload files, share — prints the folder link
  python scripts/drive_share.py kit "Folder Name" --files a.mp4 b.mp4 --emails a@x.com,b@y.com [--role reader] [--parent <id>] [--message "..."]

Default account: personal.
"""
import sys, io, os, argparse, mimetypes
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from google_auth import service  # noqa: E402
from googleapiclient.http import MediaFileUpload  # noqa: E402

FOLDER_MIME = 'application/vnd.google-apps.folder'


def mkfolder(drive, name, parent=None):
    meta = {'name': name, 'mimeType': FOLDER_MIME}
    if parent:
        meta['parents'] = [parent]
    f = drive.files().create(body=meta, fields='id,name,webViewLink').execute()
    return f


def upload(drive, folder_id, path):
    name = os.path.basename(path)
    mime = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    media = MediaFileUpload(path, mimetype=mime, resumable=True)
    f = drive.files().create(
        body={'name': name, 'parents': [folder_id]},
        media_body=media,
        fields='id,name,webViewLink',
    ).execute()
    return f


def share(drive, file_id, emails, role='reader', notify=True, message=None):
    results = []
    for email in emails:
        body = {'type': 'user', 'role': role, 'emailAddress': email}
        kw = dict(fileId=file_id, body=body, fields='id,emailAddress,role',
                  sendNotificationEmail=notify)
        if notify and message:
            kw['emailMessage'] = message
        results.append(drive.permissions().create(**kw).execute())
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--account', default='personal', choices=['personal', 'stoop'])
    sub = p.add_subparsers(dest='cmd')

    mf = sub.add_parser('mkfolder'); mf.add_argument('name'); mf.add_argument('--parent')

    up = sub.add_parser('upload'); up.add_argument('folder_id'); up.add_argument('files', nargs='+')

    sh = sub.add_parser('share')
    sh.add_argument('file_id'); sh.add_argument('--emails', required=True)
    sh.add_argument('--role', default='reader', choices=['reader', 'writer', 'commenter'])
    sh.add_argument('--no-notify', action='store_true'); sh.add_argument('--message')

    kt = sub.add_parser('kit')
    kt.add_argument('name'); kt.add_argument('--files', nargs='+', required=True)
    kt.add_argument('--emails', required=True)
    kt.add_argument('--role', default='reader', choices=['reader', 'writer', 'commenter'])
    kt.add_argument('--parent'); kt.add_argument('--message'); kt.add_argument('--no-notify', action='store_true')

    args = p.parse_args()
    if not args.cmd:
        p.print_help(); sys.exit(1)
    drive = service(args.account, 'drive', 'drive', 'v3')

    if args.cmd == 'mkfolder':
        f = mkfolder(drive, args.name, args.parent)
        print(f"folder: {f['name']}\n  id:   {f['id']}\n  link: {f['webViewLink']}")

    elif args.cmd == 'upload':
        for path in args.files:
            f = upload(drive, args.folder_id, path)
            print(f"  ↑ {f['name']}  ({f['id']})")

    elif args.cmd == 'share':
        emails = [e.strip() for e in args.emails.split(',') if e.strip()]
        res = share(drive, args.file_id, emails, args.role, not args.no_notify, args.message)
        for r in res:
            print(f"  shared with {r.get('emailAddress')} as {r.get('role')}")

    elif args.cmd == 'kit':
        emails = [e.strip() for e in args.emails.split(',') if e.strip()]
        folder = mkfolder(drive, args.name, args.parent)
        print(f"folder: {folder['name']}\n  id:   {folder['id']}\n  link: {folder['webViewLink']}")
        for path in args.files:
            if not os.path.exists(path):
                print(f"  ! missing, skipped: {path}"); continue
            f = upload(drive, folder['id'], path)
            print(f"  ↑ {f['name']}")
        res = share(drive, folder['id'], emails, args.role, not args.no_notify, args.message)
        for r in res:
            print(f"  shared with {r.get('emailAddress')} as {r.get('role')}")
        print(f"\nDONE → {folder['webViewLink']}")


if __name__ == '__main__':
    main()
