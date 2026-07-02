import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import google_auth

svc = google_auth.service('personal', 'drive', 'drive', 'v3')
for folder in sys.argv[1:]:
    try:
        res = svc.files().list(
            q=f"'{folder}' in parents and trashed=false",
            fields="files(id,name,mimeType,size,imageMediaMetadata(width,height))",
            pageSize=200, orderBy="name",
        ).execute()
    except Exception as e:
        print(f"ERR listing {folder}: {e}")
        continue
    files = res.get('files', [])
    print(f"\n===== folder {folder} : {len(files)} item(s) =====")
    for f in files:
        mt = f['mimeType'].replace('application/vnd.google-apps.', 'gapps:').replace('image/', 'img/')
        dim = f.get('imageMediaMetadata') or {}
        w, h = dim.get('width'), dim.get('height')
        orient = ''
        if w and h:
            orient = 'PORTRAIT' if h > w else 'landscape'
        d = f"{w}x{h}" if w else ''
        print(f"  {mt:14} {d:11} {orient:9} {f['name']}   [{f['id']}]")
