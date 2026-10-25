#!/usr/bin/env python3
"""Arma la edición diaria y actualiza el catálogo OPDS.

Uso:
    python3 tools/build.py ediciones/AAAA-MM-DD.md

Qué hace:
  1. Lee el markdown de la edición (formato descripto en INSTRUCCIONES.md).
  2. Genera epub/AAAA-MM-DD.epub (EPUB 3, un capítulo por sección "## ").
  3. Borra las ediciones más viejas, conservando las últimas KEEP.
  4. Regenera opds.xml (lo que lee KOReader) e index.html (para el navegador).

Sin dependencias externas: solo la biblioteca estándar de Python.
"""

import datetime as dt
import html
import json
import re
import sys
import uuid
import zipfile
from pathlib import Path

BASE_URL = "https://nahuellopezibb.github.io/Noticias"
FEED_TITLE = "Noticias del día"
AUTHOR = "Resumen diario (Claude)"
KEEP = 14  # ediciones que se conservan

ROOT = Path(__file__).resolve().parent.parent
EPUB_DIR = ROOT / "epub"
SRC_DIR = ROOT / "ediciones"
INDEX_JSON = EPUB_DIR / "index.json"
ART = dt.timezone(dt.timedelta(hours=-3))

CSS = """
body { font-family: serif; line-height: 1.45; margin: 0 0.6em; }
h1 { font-size: 1.5em; margin: 0.8em 0 0.4em; }
h2 { font-size: 1.15em; margin: 1.4em 0 0.3em; }
p { margin: 0 0 0.7em; text-align: justify; }
.src { font-size: 0.8em; margin-top: -0.3em; }
.intro { font-style: italic; }
ul { margin: 0 0 0.8em 1.1em; padding: 0; }
li { margin-bottom: 0.3em; }
a { color: inherit; }
"""


# ---------------------------------------------------------------- markdown

def inline(text: str) -> str:
    """Escapa HTML y convierte **negrita**, *cursiva* y [texto](url)."""
    out = html.escape(text, quote=False)
    out = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
                 lambda m: f'<a href="{html.escape(m.group(2))}">{m.group(1)}</a>', out)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", out)
    return out


def blocks_to_html(lines):
    """Convierte las líneas de una sección en HTML (### títulos, listas, párrafos)."""
    parts, para, items = [], [], []

    def flush():
        nonlocal para, items
        if para:
            text = " ".join(para)
            cls = ' class="src"' if text.lower().startswith(("fuente", "fuentes")) else ""
            parts.append(f"<p{cls}>{inline(text)}</p>")
            para = []
        if items:
            parts.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>")
            items = []

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush()
        elif line.startswith("### "):
            flush()
            parts.append(f"<h2>{inline(line[4:].strip())}</h2>")
        elif re.match(r"^\s*[-*] ", line):
            if para:
                flush()
            items.append(re.sub(r"^\s*[-*] ", "", line).strip())
        else:
            if items:
                flush()
            para.append(line.strip())
    flush()
    return "\n".join(parts)


def parse_edition(md: str):
    title, intro, sections, current = None, [], [], None
    for line in md.splitlines():
        if line.startswith("# ") and title is None:
            title = line[2:].strip()
        elif line.startswith("## "):
            current = {"title": line[3:].strip(), "lines": []}
            sections.append(current)
        elif current is None:
            intro.append(line)
        else:
            current["lines"].append(line)
    if not title or not sections:
        sys.exit("La edición necesita un título '# ...' y al menos una sección '## ...'")
    return title, intro, sections


# --------------------------------------------------------------------- epub

def xhtml(title, body):
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="es" xml:lang="es">
<head><meta charset="utf-8"/><title>{html.escape(title)}</title>
<link rel="stylesheet" type="text/css" href="style.css"/></head>
<body>
{body}
</body></html>
"""


def build_epub(date: str, title: str, intro, sections, out: Path):
    book_id = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, BASE_URL + '/' + date)}"
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    chapters = []  # (filename, title, xhtml)
    intro_html = blocks_to_html(intro)
    toc_list = "".join(f"<li>{html.escape(s['title'])}</li>" for s in sections)
    cover_body = (f"<h1>{html.escape(title)}</h1>\n"
                  + (f'<div class="intro">{intro_html}</div>\n' if intro_html else "")
                  + f"<p><strong>Secciones:</strong></p><ul>{toc_list}</ul>")
    chapters.append(("portada.xhtml", "Portada", xhtml(title, cover_body)))
    for n, sec in enumerate(sections, 1):
        body = f"<h1>{html.escape(sec['title'])}</h1>\n{blocks_to_html(sec['lines'])}"
        chapters.append((f"sec{n:02d}.xhtml", sec["title"], xhtml(sec["title"], body)))

    manifest = "\n".join(
        f'    <item id="c{i}" href="{f}" media-type="application/xhtml+xml"/>'
        for i, (f, _, _) in enumerate(chapters))
    spine = "\n".join(f'    <itemref idref="c{i}"/>' for i in range(len(chapters)))
    opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="es">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">{book_id}</dc:identifier>
    <dc:title>{html.escape(title)}</dc:title>
    <dc:creator>{html.escape(AUTHOR)}</dc:creator>
    <dc:language>es</dc:language>
    <dc:date>{date}</dc:date>
    <meta property="dcterms:modified">{now}</meta>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="css" href="style.css" media-type="text/css"/>
{manifest}
  </manifest>
  <spine toc="ncx">
{spine}
  </spine>
</package>
"""
    nav_items = "".join(f'<li><a href="{f}">{html.escape(t)}</a></li>' for f, t, _ in chapters)
    nav = xhtml("Índice", f'<nav epub:type="toc" id="toc"><h1>Índice</h1><ol>{nav_items}</ol></nav>')
    points = "".join(
        f'<navPoint id="p{i}" playOrder="{i + 1}"><navLabel><text>{html.escape(t)}</text></navLabel>'
        f'<content src="{f}"/></navPoint>' for i, (f, t, _) in enumerate(chapters))
    ncx = f"""<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<head><meta name="dtb:uid" content="{book_id}"/></head>
<docTitle><text>{html.escape(title)}</text></docTitle>
<navMap>{points}</navMap>
</ncx>
"""
    container = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>
"""
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w") as z:
        # "mimetype" tiene que ir primero y sin comprimir (requisito de EPUB)
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", opf, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/nav.xhtml", nav, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/toc.ncx", ncx, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/style.css", CSS, compress_type=zipfile.ZIP_DEFLATED)
        for f, _, body in chapters:
            z.writestr(f"OEBPS/{f}", body, compress_type=zipfile.ZIP_DEFLATED)


# ------------------------------------------------------------ opds / index

def write_catalog(index: dict):
    now = dt.datetime.now(ART).isoformat(timespec="seconds")
    entries = []
    for date in sorted(index, reverse=True):
        e = index[date]
        url = f"{BASE_URL}/epub/{date}.epub"
        entries.append(f"""  <entry>
    <title>{html.escape(e['title'])}</title>
    <id>urn:noticias:{date}</id>
    <updated>{e['updated']}</updated>
    <author><name>{html.escape(AUTHOR)}</name></author>
    <dc:language>es</dc:language>
    <summary>{html.escape(e['summary'])}</summary>
    <link rel="http://opds-spec.org/acquisition" href="{url}" type="application/epub+zip"/>
  </entry>""")
    feed = f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/terms/" xmlns:opds="http://opds-spec.org/2010/catalog">
  <id>urn:noticias:catalogo</id>
  <title>{html.escape(FEED_TITLE)}</title>
  <updated>{now}</updated>
  <author><name>{html.escape(AUTHOR)}</name></author>
  <link rel="self" href="{BASE_URL}/opds.xml" type="application/atom+xml;profile=opds-catalog;kind=acquisition"/>
  <link rel="start" href="{BASE_URL}/opds.xml" type="application/atom+xml;profile=opds-catalog;kind=acquisition"/>
{chr(10).join(entries)}
</feed>
"""
    (ROOT / "opds.xml").write_text(feed, encoding="utf-8")

    rows = "".join(
        f'<li><a href="epub/{d}.epub">{html.escape(index[d]["title"])}</a></li>'
        for d in sorted(index, reverse=True))
    page = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(FEED_TITLE)}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:40rem;margin:2rem auto;padding:0 1rem;line-height:1.5}}</style>
</head><body>
<h1>{html.escape(FEED_TITLE)}</h1>
<p>Catálogo OPDS para KOReader: <code>{BASE_URL}/opds.xml</code></p>
<ul>{rows}</ul>
</body></html>
"""
    (ROOT / "index.html").write_text(page, encoding="utf-8")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1]).resolve()
    date = src.stem
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        sys.exit("El archivo tiene que llamarse AAAA-MM-DD.md")

    title, intro, sections = parse_edition(src.read_text(encoding="utf-8"))
    build_epub(date, title, intro, sections, EPUB_DIR / f"{date}.epub")

    index = json.loads(INDEX_JSON.read_text(encoding="utf-8")) if INDEX_JSON.exists() else {}
    index[date] = {
        "title": title,
        "summary": "Secciones: " + " · ".join(s["title"] for s in sections),
        "updated": dt.datetime.now(ART).isoformat(timespec="seconds"),
    }

    # conservar solo las últimas KEEP ediciones
    for old in sorted(index)[:-KEEP]:
        index.pop(old)
        (EPUB_DIR / f"{old}.epub").unlink(missing_ok=True)
        (SRC_DIR / f"{old}.md").unlink(missing_ok=True)

    INDEX_JSON.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    write_catalog(index)
    (ROOT / ".nojekyll").touch()
    print(f"OK: epub/{date}.epub — {len(sections)} secciones — {len(index)} ediciones en el catálogo")


if __name__ == "__main__":
    main()
