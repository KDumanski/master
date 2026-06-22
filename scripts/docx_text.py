"""
Extract plain text from a Google Drive file that is an uploaded .docx
(which the Drive API can't `export` as text). Downloads the bytes and
pulls the paragraph text out of word/document.xml.

Usage: python scripts/docx_text.py <fileId> [--account personal|stoop]
"""
import sys, io, os, re, zipfile, html
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from google_auth import service  # noqa: E402

file_id = sys.argv[1]
account = 'personal'
if '--account' in sys.argv:
    account = sys.argv[sys.argv.index('--account') + 1]

drive = service(account, 'drive', 'drive', 'v3')
data = drive.files().get_media(fileId=file_id).execute()  # raw bytes

with zipfile.ZipFile(io.BytesIO(data)) as z:
    xml = z.read('word/document.xml').decode('utf-8', 'replace')

# paragraph + line breaks → newlines, tabs → tab, then strip the rest of the tags
xml = re.sub(r'</w:p>', '\n', xml)
xml = re.sub(r'<w:br[^>]*/>', '\n', xml)
xml = re.sub(r'<w:tab[^>]*/>', '\t', xml)
text = re.sub(r'<[^>]+>', '', xml)
text = html.unescape(text)
# collapse runs of blank lines
text = re.sub(r'\n[ \t]*\n[ \t]*\n+', '\n\n', text)
print(text.strip())
