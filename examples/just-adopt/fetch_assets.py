"""Download the only third-party asset this example needs: the Geist font (OFL), into fonts/."""
import urllib.request
from pathlib import Path
H = Path(__file__).parent
dest = H / "fonts/geist-latin.woff2"; dest.parent.mkdir(exist_ok=True)
dest.write_bytes(urllib.request.urlopen(urllib.request.Request(
    "https://fonts.gstatic.com/s/geist/v5/gyByhwUxId8gMEwcGFWNOITd.woff2", headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read())
print("ok", dest.relative_to(H))
