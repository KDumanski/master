import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import google_auth
from googleapiclient.http import MediaIoBaseDownload

svc = google_auth.service('personal', 'drive', 'drive', 'v3')
outdir = sys.argv[1]
os.makedirs(outdir, exist_ok=True)
for fid in sys.argv[2:]:
    meta = svc.files().get(fileId=fid, fields="name").execute()
    name = meta['name'].replace(' ', '_')
    req = svc.files().get_media(fileId=fid)
    path = os.path.join(outdir, f"{fid[:6]}_{name}")
    with open(path, 'wb') as fh:
        dl = MediaIoBaseDownload(fh, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
    print("downloaded", path)
