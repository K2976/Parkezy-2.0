"""A tiny single-page PDF writer for receipts: text only, built-in Helvetica, no dependencies.

Keeps the deploy free of native libraries; receipts never need more than lines of text."""

from dataclasses import dataclass

PAGE_W, PAGE_H = 595, 842  # A4 in points
MARGIN = 56


@dataclass(frozen=True)
class Line:
    text: str
    size: int = 11
    bold: bool = False
    right: str | None = None  # optional right-aligned column (amounts)
    gap_before: int = 0


def _escape(text: str) -> str:
    # Helvetica with WinAnsi covers Latin-1; anything else (e.g. the rupee sign) becomes '?'.
    safe = text.encode("latin-1", "replace").decode("latin-1")
    return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _text_width(text: str, size: int) -> float:
    return len(text) * size * 0.5  # Helvetica averages ~0.5 em per glyph: good enough to right-align


def render(lines: list[Line], *, title: str) -> bytes:
    ops, y = [], PAGE_H - MARGIN
    for line in lines:
        y -= line.gap_before + line.size + 6
        font = "F2" if line.bold else "F1"
        ops.append(f"BT /{font} {line.size} Tf {MARGIN} {y} Td ({_escape(line.text)}) Tj ET")
        if line.right is not None:
            x = PAGE_W - MARGIN - _text_width(line.right, line.size)
            ops.append(f"BT /{font} {line.size} Tf {x:.1f} {y} Td ({_escape(line.right)}) Tj ET")
    content = "\n".join(ops).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
            "/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>"
        ).encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        f"<< /Title ({_escape(title)}) /Producer (Parkezy) >>".encode("latin-1"),
    ]
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info {len(objects)} 0 R >>\n".encode()
    out += f"startxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)
