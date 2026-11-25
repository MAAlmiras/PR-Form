"""Build the sample Internal Purchase Request PDF.

Pipeline (the same one the document service will run in production):
  1. Render the HTML template with the PR data, company settings and signatures.
  2. Print it to PDF with headless Chromium (Playwright).
  3. Apply a PAdES digital seal (pyHanko) with an RFC 3161 timestamp.

Usage:
  python build_sample.py [output.pdf]

The sample uses a throwaway self-signed seal certificate generated on the fly.
Production uses the company seal certificate kept in a secret store.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import io
import json
import math
import random
import sys
from pathlib import Path

import qrcode
import qrcode.image.svg
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
BRAND = HERE / "brand"
SEAL_CN = "Almiras PR System Document Seal (SAMPLE)"
TSA_URL = "http://timestamp.digicert.com"


def data_uri(path: Path, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


# --- 1. Signature images -----------------------------------------------------
# In the app every user draws their own signature once in their settings.
# For the sample we synthesise three handwritten-looking signatures.

def _catmull_rom(points: list[tuple[float, float]]) -> str:
    d = f"M{points[0][0]:.1f},{points[0][1]:.1f}"
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i else points[0]
        p1, p2 = points[i], points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def signature_svg(seed: int) -> str:
    rnd = random.Random(seed)
    pts: list[tuple[float, float]] = []
    base = 60 + rnd.uniform(-4, 4)

    def capital(x0: float, size: float) -> float:
        cx, cy = x0 + size * 0.55, base - size * 0.75
        rx, ry, tilt = size * rnd.uniform(0.45, 0.7), size * rnd.uniform(0.8, 1.05), rnd.uniform(-0.6, -0.1)
        turns = rnd.uniform(1.9, 2.5)
        for k in range(16):
            a = math.pi * 0.6 + k / 15 * math.pi * turns
            x, y = rx * math.cos(a), ry * math.sin(a)
            pts.append((cx + x * math.cos(tilt) - y * math.sin(tilt), cy + x * math.sin(tilt) + y * math.cos(tilt)))
        return pts[-1][0] + 4

    def run(x: float, n: int, height: float) -> float:
        for i in range(n):
            h = height * (1 - i / (n + 3)) * rnd.uniform(0.6, 1.2)
            step = rnd.uniform(7, 15)
            if rnd.random() < 0.3:
                pts.extend([(x + step * 0.6, base - h), (x + step * 0.2, base - h * 1.3),
                            (x - step * 0.1, base - h * 0.7), (x + step, base)])
            else:
                pts.extend([(x + step * 0.5, base - h), (x + step, base + rnd.uniform(-2, 2))])
            x += step
        return x

    x = capital(8, rnd.uniform(26, 34))
    x = run(x, rnd.randint(4, 6), rnd.uniform(14, 22))
    if True:  # surname
        x = capital(x + 2, rnd.uniform(20, 28))
        x = run(x, rnd.randint(4, 7), rnd.uniform(10, 18))
    end = (x + rnd.uniform(4, 14), base + rnd.uniform(6, 12))
    pts += [end, (end[0] - 8, base + 18), (rnd.uniform(10, 40), base + rnd.uniform(10, 20))]
    width = max(p[0] for p in pts) + 12
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} 92">'
            f'<path d="{_catmull_rom(pts)}" fill="none" stroke="#1c2f6e" stroke-width="2.4" '
            f'stroke-linecap="round" stroke-linejoin="round"/></svg>')


# --- 2. Fingerprints ----------------------------------------------------------

def content_hash(pr: dict) -> str:
    """Canonical hash of what signers approve: header fields and every item."""
    canonical = {k: pr[k] for k in ("number", "revision", "project_name", "project_number", "date",
                                    "required_by", "deliver_to", "notes", "items")}
    blob = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def signature_id(chash: str, signer: dict) -> str:
    raw = hashlib.sha256(f"{chash}|{signer['role']}|{signer['signed_at']}".encode()).hexdigest()[:20].upper()
    return "-".join(raw[i:i + 4] for i in range(0, 20, 4))


def qr_svg(text: str) -> str:
    img = qrcode.make(text, image_factory=qrcode.image.svg.SvgPathImage, border=0,
                      error_correction=qrcode.constants.ERROR_CORRECT_M)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode()
    return svg[svg.index("<svg"):].replace('fill="#000000"', 'fill="#0b2a3c"')


# --- 3. Render, print, seal --------------------------------------------------

def render_html(data: dict) -> str:
    pr = data["pr"]
    chash = content_hash(pr)
    signers = []
    for s in data["signers"]:
        signers.append({**s, "svg": signature_svg(s["seed"]), "sig_id": signature_id(chash, s)})
    company = {**data["company"], "logo_src": data_uri(BRAND / data["company"]["logo"], "image/png")}
    issuer = {**data["issuer"], "logo_src": data_uri(BRAND / data["issuer"]["logo"], "image/png")}
    verify_url = data["issuer"]["verify_base_url"] + pr["number"]
    fonts = {
        "rakik_regular": data_uri(BRAND / "fonts/HTRakik-Regular.woff2", "font/woff2"),
        "rakik_semibold": data_uri(BRAND / "fonts/HTRakik-SemiBold.woff2", "font/woff2"),
        "bricolage_bold": data_uri(BRAND / "fonts/BricolageGrotesque-Bold.ttf", "font/ttf"),
    }
    env = Environment(loader=FileSystemLoader(HERE), autoescape=True)
    return env.get_template("template.html.j2").render(
        sample=True, pr=pr, company=company, issuer=issuer, signers=signers, history=data["history"],
        fonts=fonts, content_hash=chash, verify_url=verify_url.replace("https://", ""),
        qr_svg=qr_svg(verify_url), filler_rows=max(0, 14 - len(pr["items"])),
        sealed_at=data["history"][-1]["at"], seal_cn=SEAL_CN,
    )


def print_pdf(html: str) -> bytes:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="load")
        page.evaluate("document.fonts.ready")
        pdf = page.pdf(format="A4", print_background=True, prefer_css_page_size=True)
        browser.close()
    return pdf


def make_sample_seal_identity():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    name = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "SA"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Almiras Holding"),
        x509.NameAttribute(NameOID.COMMON_NAME, SEAL_CN),
    ])
    now = dt.datetime.now(dt.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(days=1)).not_valid_after(now + dt.timedelta(days=365))
            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=True, key_encipherment=False,
                                         data_encipherment=False, key_agreement=False, key_cert_sign=False,
                                         crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
            .sign(key, hashes.SHA256()))
    return (key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                              serialization.NoEncryption()),
            cert.public_bytes(serialization.Encoding.PEM))


def seal_pdf(pdf: bytes, pr_number: str) -> tuple[bytes, bool]:
    from asn1crypto import keys, pem, x509 as ax509
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import signers, timestamps
    from pyhanko.sign.fields import MDPPerm, SigSeedSubFilter

    key_pem, cert_pem = make_sample_seal_identity()
    signer = signers.SimpleSigner(
        signing_cert=ax509.Certificate.load(pem.unarmor(cert_pem)[2]),
        signing_key=keys.PrivateKeyInfo.load(pem.unarmor(key_pem)[2]),
        cert_registry=None,
    )
    meta = signers.PdfSignatureMetadata(
        field_name="AlmirasSeal", subfilter=SigSeedSubFilter.PADES, md_algorithm="sha256",
        reason=f"Approved internal purchase request {pr_number}", location="Riyadh, Saudi Arabia",
        certify=True, docmdp_permissions=MDPPerm.NO_CHANGES,
    )
    for tsa in (timestamps.HTTPTimeStamper(TSA_URL), None):
        try:
            out = io.BytesIO()
            signers.sign_pdf(IncrementalPdfFileWriter(io.BytesIO(pdf)), meta, signer=signer,
                             timestamper=tsa, output=out)
            return out.getvalue(), tsa is not None
        except Exception as exc:  # timestamp server unreachable: seal without it
            if tsa is None:
                raise
            print(f"Timestamp server failed ({exc}); sealing without timestamp", file=sys.stderr)
    raise RuntimeError("unreachable")


def main() -> None:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "sample.pdf"
    data = json.loads((HERE / "sample_data.json").read_text())
    html = render_html(data)
    (out_path.with_suffix(".html")).write_text(html)
    pdf = print_pdf(html)
    sealed, stamped = seal_pdf(pdf, data["pr"]["number"])
    out_path.write_bytes(sealed)
    print(f"Wrote {out_path} ({len(sealed) // 1024} KB, timestamp: {'yes' if stamped else 'no'})")


if __name__ == "__main__":
    main()
