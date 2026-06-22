"""
One-off Drive inventory: list everything shared with the personal account
and recursively walk a given folder, reporting quality metadata
(dimensions, byte size, type) so we can sort high- vs low-res images.

Usage:
  python scripts/drive_inventory.py shared            # what was recently shared with me
  python scripts/drive_inventory.py folder <folderId> # recursive contents of a folder
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from google_auth import service  # noqa: E402

FIELDS = ("files(id,name,mimeType,size,modifiedTime,createdTime,"
          "imageMediaMetadata(width,height),owners(emailAddress,displayName),"
          "shared,sharedWithMeTime,parents,webViewLink,videoMediaMetadata(width,height))")

drive = service('personal', 'drive', 'drive', 'v3')


def human(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ''
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == 'B' else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def row(f):
    img = f.get('imageMediaMetadata') or f.get('videoMediaMetadata') or {}
    dims = f"{img.get('width')}x{img.get('height')}" if img.get('width') else ''
    owner = (f.get('owners') or [{}])[0].get('emailAddress', '')
    mime = f.get('mimeType', '').split('/')[-1]
    print(f"\t{mime:14s}\t{dims:11s}\t{human(f.get('size')):9s}\t{f.get('modifiedTime','')[:10]}\t{owner:32s}\t{f.get('name','')}")
    print(f"\t  id={f.get('id')}  {f.get('webViewLink','')}")


def list_children(folder_id):
    out, token = [], None
    while True:
        res = drive.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            pageSize=200, fields=f"nextPageToken,{FIELDS}", pageToken=token,
            orderBy='folder,name').execute()
        out.extend(res.get('files', []))
        token = res.get('nextPageToken')
        if not token:
            break
    return out


def walk(folder_id, depth=0):
    children = list_children(folder_id)
    for f in children:
        print('  ' * depth, end='')
        row(f)
        if f.get('mimeType') == 'application/vnd.google-apps.folder':
            walk(f['id'], depth + 1)


def shared():
    res = drive.files().list(
        q="sharedWithMe = true and trashed = false",
        pageSize=100, fields=f"nextPageToken,{FIELDS}",
        orderBy='sharedWithMeTime desc').execute()
    files = res.get('files', [])
    print(f"\n{len(files)} item(s) shared with me (most recent first):\n")
    for f in files:
        shared_when = f.get('sharedWithMeTime', '')[:10]
        print(f"shared {shared_when}", end='')
        row(f)
        if f.get('mimeType') == 'application/vnd.google-apps.folder':
            walk(f['id'], 1)


def tier(f):
    """Classify a file into a usefulness/quality bucket."""
    mime = f.get('mimeType', '')
    name = f.get('name', '').lower()
    if mime == 'application/vnd.google-apps.folder':
        return 'folder'
    if 'pdf' in mime or name.endswith('.pdf'):
        return 'doc(pdf)'
    if name.endswith(('.doc', '.docx')) or 'document' in mime:
        return 'doc(word)'
    if 'video' in mime or name.endswith(('.mov', '.mp4')):
        return 'video'
    if 'tiff' in mime or name.endswith(('.tif', '.tiff')):
        return 'tiff(print)'
    if name == '.ds_store' or 'octet-stream' in mime:
        return 'junk(.DS_Store)'
    img = f.get('imageMediaMetadata') or {}
    long_edge = max(img.get('width') or 0, img.get('height') or 0)
    if long_edge == 0:
        return 'image(no-dims)'
    if long_edge >= 3000:
        return 'A: print/hero (>=3000px)'
    if long_edge >= 1500:
        return 'B: web-good (1500-3000px)'
    if long_edge >= 800:
        return 'C: web-ok (800-1500px)'
    return 'D: low/snapshot (<800px)'


def collect(folder_id):
    """Recursively gather all leaf files under a folder."""
    leaves = []
    for f in list_children(folder_id):
        if f.get('mimeType') == 'application/vnd.google-apps.folder':
            leaves += collect(f['id'])
        else:
            leaves.append(f)
    return leaves


def summarize(folder_id):
    top = list_children(folder_id)
    grand_tiers, grand_size, grand_n = {}, 0, 0
    print("\n===== PER TOP-LEVEL ITEM =====\n")
    print(f"{'item':52s} {'files':>5s} {'size':>9s}  tier breakdown")
    print('-' * 110)
    docs_global, loose = [], []
    for f in sorted(top, key=lambda x: x.get('name', '')):
        if f.get('mimeType') == 'application/vnd.google-apps.folder':
            leaves = collect(f['id'])
        else:
            leaves = [f]
            loose.append(f)
        tiers, size = {}, 0
        for lf in leaves:
            t = tier(lf)
            tiers[t] = tiers.get(t, 0) + 1
            try:
                size += int(lf.get('size') or 0)
            except ValueError:
                pass
            grand_tiers[t] = grand_tiers.get(t, 0) + 1
            if t.startswith('doc'):
                docs_global.append(lf.get('name', ''))
        grand_size += size
        grand_n += len(leaves)
        kind = 'DIR ' if f.get('mimeType', '').endswith('folder') else 'FILE'
        breakdown = ', '.join(f"{k.split(':')[0] if ':' in k else k}:{v}"
                              for k, v in sorted(tiers.items()))
        print(f"[{kind}] {f.get('name','')[:46]:46s} {len(leaves):5d} {human(size):>9s}  {breakdown}")

    print('\n' + '=' * 60)
    print(f"GRAND TOTAL: {grand_n} files, {human(grand_size)}")
    print('=' * 60)
    for k, v in sorted(grand_tiers.items()):
        print(f"  {k:32s} {v}")
    print(f"\nDocuments (text / press / CV / statements): {len(docs_global)}")
    for d in docs_global:
        print(f"  - {d}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    if sys.argv[1] == 'shared':
        shared()
    elif sys.argv[1] == 'folder':
        print(f"\nRecursive contents of folder {sys.argv[2]}:\n")
        walk(sys.argv[2])
    elif sys.argv[1] == 'summary':
        summarize(sys.argv[2])
    elif sys.argv[1] == 'usable':
        # list only high-res, web-usable assets grouped by top-level item
        top = list_children(sys.argv[2])
        total = 0
        for f in sorted(top, key=lambda x: x.get('name', '')):
            leaves = collect(f['id']) if f.get('mimeType', '').endswith('folder') else [f]
            good = [lf for lf in leaves
                    if tier(lf).startswith('A') or tier(lf) == 'tiff(print)'
                    or (tier(lf).startswith('B'))]
            if not good:
                continue
            print(f"\n### {f.get('name','')}  ({len(good)} usable)")
            for lf in sorted(good, key=lambda x: x.get('name', '')):
                img = lf.get('imageMediaMetadata') or {}
                dims = f"{img.get('width')}x{img.get('height')}" if img.get('width') else 'TIFF'
                t = 'A' if tier(lf).startswith('A') else ('TIFF' if tier(lf) == 'tiff(print)' else 'B')
                print(f"  [{t:4s}] {dims:11s} {human(lf.get('size')):>8s}  {lf.get('name','')}")
                total += 1
        print(f"\nTOTAL usable (A + TIFF + B): {total}")
