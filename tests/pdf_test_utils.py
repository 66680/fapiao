from __future__ import annotations

from pathlib import Path


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_text_pdf(path: Path, pages: list[list[str]]) -> None:
    if not pages:
        pages = [[""]]

    objects: list[bytes] = []

    def add_object(payload: bytes | str) -> int:
        data = payload.encode("latin-1") if isinstance(payload, str) else payload
        objects.append(data)
        return len(objects)

    font_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids: list[int] = []

    for lines in pages:
        text_lines = [line for line in lines if line is not None]
        commands = ["BT", "/F1 12 Tf"]
        y = 760
        for line in text_lines:
            escaped = _escape_pdf_text(str(line))
            commands.append(f"1 0 0 1 72 {y} Tm ({escaped}) Tj")
            y -= 18
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1")
        content_id = add_object(
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
        )
        page_id = add_object(
            f"<< /Type /Page /Parent {{PAGES}} 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        )
        page_ids.append(page_id)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    pages_id = add_object(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>")
    catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

    # Replace parent placeholder for each page object.
    for page_id in page_ids:
        payload = objects[page_id - 1].decode("latin-1").replace("{PAGES}", str(pages_id))
        objects[page_id - 1] = payload.encode("latin-1")

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    chunks = bytearray(header)
    offsets = [0]
    for index, payload in enumerate(objects, start=1):
        offsets.append(len(chunks))
        chunks.extend(f"{index} 0 obj\n".encode("ascii"))
        chunks.extend(payload)
        chunks.extend(b"\nendobj\n")

    xref_pos = len(chunks)
    chunks.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    chunks.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        chunks.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    chunks.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n"
        ).encode("ascii")
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(chunks))

