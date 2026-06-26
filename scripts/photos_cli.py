"""
Google Photos access for the masters repo, via the Photos Picker API.

Why the Picker API: Google removed the old "read the whole library" scopes in
March 2025. An app can no longer list/search a user's entire Google Photos.
Instead the user opens a Google-hosted picker, selects exactly the items they
want to share, and the app fetches only those. That fits our use case (the user
selects specific photos) and is the only supported path today.

Flow:
  1. create a session            -> pickerUri + sessionId
  2. user opens pickerUri, selects photos, taps "Done" in Google Photos
  3. poll the session            -> wait until mediaItemsSet == true
  4. list the picked media items
  5. download each (baseUrl + '=d' for photos / '=dv' for video, Bearer auth)
  6. (optional) upload each straight into a Drive folder

Requires:
  - Photos Picker API enabled on the OAuth client's GCP project
    (photospicker.googleapis.com)
  - a 'photos' token (run: python scripts/google_auth.py consent
    --account personal --capability photos)

Usage:
  python scripts/photos_cli.py pick --download .secrets/photos_pull
  python scripts/photos_cli.py pick --download .secrets/photos_pull --to-drive <FOLDER_ID>
"""
import sys, io, os, time, argparse, mimetypes

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from google_auth import get_credentials, service  # noqa: E402
from google.auth.transport.requests import AuthorizedSession  # noqa: E402

BASE = 'https://photospicker.googleapis.com/v1'


def authed(account):
    creds = get_credentials(account, 'photos', allow_consent=False)
    return AuthorizedSession(creds)


def create_session(sess):
    r = sess.post(f'{BASE}/sessions', json={})
    r.raise_for_status()
    return r.json()


def _interval_seconds(session, fallback):
    """Honor the server's recommended poll interval (a duration like '5s')."""
    pc = (session or {}).get('pollingConfig') or {}
    raw = pc.get('pollInterval')
    if isinstance(raw, str) and raw.endswith('s'):
        try:
            return max(1.0, float(raw[:-1]))
        except ValueError:
            pass
    return fallback


def poll_session(sess, sid, timeout, interval):
    waited = 0.0
    while waited < timeout:
        r = sess.get(f'{BASE}/sessions/{sid}')
        r.raise_for_status()
        j = r.json()
        if j.get('mediaItemsSet'):
            return j
        step = _interval_seconds(j, interval)
        time.sleep(step)
        waited += step
    return None


def list_items(sess, sid):
    items, token = [], None
    while True:
        params = {'sessionId': sid, 'pageSize': 100}
        if token:
            params['pageToken'] = token
        r = sess.get(f'{BASE}/mediaItems', params=params)
        r.raise_for_status()
        j = r.json()
        items.extend(j.get('mediaItems', []))
        token = j.get('nextPageToken')
        if not token:
            break
    return items


def download(sess, item, outdir):
    mf = item.get('mediaFile', {})
    base = mf['baseUrl']
    suffix = '=dv' if item.get('type') == 'VIDEO' else '=d'
    r = sess.get(base + suffix)
    r.raise_for_status()
    name = mf.get('filename')
    if not name:
        ext = mimetypes.guess_extension(mf.get('mimeType', '') or '') or ''
        name = f"{item.get('id', 'item')[:16]}{ext}"
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, name)
    # de-dupe if two picked items share a filename
    n = 1
    stem, ext = os.path.splitext(path)
    while os.path.exists(path):
        path = f"{stem}_{n}{ext}"
        n += 1
    with open(path, 'wb') as f:
        f.write(r.content)
    return path, len(r.content), mf.get('mimeType', '')


def upload_to_drive(account, path, mime, folder_id):
    from googleapiclient.http import MediaFileUpload
    drv = service(account, 'drive', 'drive', 'v3')
    media = MediaFileUpload(path, mimetype=mime or 'application/octet-stream', resumable=False)
    f = drv.files().create(
        body={'name': os.path.basename(path), 'parents': [folder_id]},
        media_body=media, fields='id,webViewLink',
    ).execute()
    return f.get('webViewLink', f.get('id'))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--account', default='personal', choices=['personal', 'stoop'])
    sub = p.add_subparsers(dest='cmd')

    pk = sub.add_parser('pick', help='Open a picker, then download what the user selects')
    pk.add_argument('--download', default=os.path.join('.secrets', 'photos_pull'),
                    help='Local folder to save selected photos into')
    pk.add_argument('--to-drive', dest='to_drive', default=None,
                    help='Drive folder id to also upload the selected photos into')
    pk.add_argument('--timeout', type=int, default=540, help='Seconds to wait for selection')
    pk.add_argument('--interval', type=float, default=4.0, help='Default poll interval (s)')

    args = p.parse_args()
    if not args.cmd:
        p.print_help(); sys.exit(1)

    sess = authed(args.account)

    if args.cmd == 'pick':
        s = create_session(sess)
        sid = s['id']
        print('\n' + '=' * 64)
        print('  OPEN THIS URL, SELECT YOUR PHOTOS, THEN TAP "DONE":')
        print('  ' + s['pickerUri'])
        print('=' * 64)
        print(f'  (session {sid} — waiting up to {args.timeout}s for your selection)\n')
        sys.stdout.flush()

        done = poll_session(sess, sid, args.timeout, args.interval)
        if not done:
            print('TIMED OUT — no selection received. Re-run and pick faster, '
                  'or increase --timeout.')
            sys.exit(2)

        items = list_items(sess, sid)
        print(f'Selected {len(items)} item(s). Downloading...\n')
        outdir = args.download
        saved = []
        for it in items:
            path, size, mime = download(sess, it, outdir)
            saved.append((path, mime))
            line = f'  saved {os.path.basename(path)}  ({size//1024} KB, {mime})'
            if args.to_drive:
                link = upload_to_drive(args.account, path, mime, args.to_drive)
                line += f'\n        -> Drive: {link}'
            print(line)

        print(f'\nDone. {len(saved)} file(s) in: {os.path.abspath(outdir)}')


if __name__ == '__main__':
    main()
