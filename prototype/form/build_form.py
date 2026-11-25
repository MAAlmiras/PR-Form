"""Inline fonts, logo and a sample signature into the form prototype.

Usage: python build_form.py <output.html>
"""
import base64, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRAND = HERE.parent / "pdf" / "brand"
sys.path.insert(0, str(HERE.parent / "pdf"))
from build_sample import signature_svg  # noqa: E402


def uri(path: Path, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


html = (HERE / "form.src.html").read_text()
subs = {
    "__RAKIK400__": uri(BRAND / "fonts/HTRakik-Regular.woff2", "font/woff2"),
    "__RAKIK600__": uri(BRAND / "fonts/HTRakik-SemiBold.woff2", "font/woff2"),
    "__BRIC700__": uri(BRAND / "fonts/BricolageGrotesque-Bold.ttf", "font/ttf"),
    "__LOGO_WHITE__": uri(BRAND / "logos/almiras-logo-en-white.png", "image/png"),
    "__SIG__": "data:image/svg+xml;base64," + base64.b64encode(signature_svg(11).encode()).decode(),
}
for k, v in subs.items():
    html = html.replace(k, v)
Path(sys.argv[1]).write_text(html)
print(f"Wrote {sys.argv[1]} ({len(html) // 1024} KB)")
