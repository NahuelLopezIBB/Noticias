#!/usr/bin/env python3
"""Arma la edición diaria y actualiza el catálogo OPDS.

Uso:
    python3 tools/build.py ediciones/AAAA-MM-DD.md          (edición diaria)
    python3 tools/build.py ediciones/AAAA-MM-DD-tema.md     (informe a pedido)

Qué hace:
  1. Lee el markdown de la edición (formato descripto en INSTRUCCIONES.md).
  2. Genera epub/AAAA-MM-DD.epub (EPUB 3, un capítulo por sección "## ")
     y web/AAAA-MM-DD.html (versión para leer en el navegador).
  3. Borra las ediciones e informes de más de KEEP días.
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
KEEP = 14  # días que se conservan

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
table { border-collapse: collapse; width: 100%; margin: 0.4em 0 1em; font-size: 0.85em; line-height: 1.25; }
th, td { border: 1px solid #000; padding: 0.25em 0.35em; text-align: left; vertical-align: top; }
th { font-weight: bold; }
td.num, th.num { text-align: right; }
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


def split_row(line: str):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def table_html(rows) -> str:
    """Tabla markdown (| a | b |) -> <table>. La fila |---| separa el encabezado."""
    sep = next((i for i, r in enumerate(rows) if re.fullmatch(r"\|?[\s:|-]+\|?", r.strip())), None)
    head = [split_row(r) for r in rows[:sep]] if sep is not None else []
    body = [split_row(r) for r in (rows[sep + 1:] if sep is not None else rows)]
    is_num = lambda c: bool(re.fullmatch(r"[+\-−]?[\d.,\s%]+(\([\d.,\s%]+\))?", c)) and any(ch.isdigit() for ch in c)

    def cells(row, tag):
        return "".join(
            f'<{tag}{" class=\"num\"" if tag == "td" and is_num(c) else ""}>{inline(c)}</{tag}>'
            for c in row)

    out = "<table>"
    if head:
        out += "<thead>" + "".join(f"<tr>{cells(r, 'th')}</tr>" for r in head) + "</thead>"
    out += "<tbody>" + "".join(f"<tr>{cells(r, 'td')}</tr>" for r in body) + "</tbody></table>"
    return out


def blocks_to_html(lines):
    """Convierte las líneas de una sección en HTML (### títulos, listas, tablas, párrafos)."""
    parts, para, items, table = [], [], [], []

    def flush():
        nonlocal para, items, table
        if table:
            parts.append(table_html(table))
            table = []
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
        elif line.lstrip().startswith("|"):
            if para or items:
                flush()
            table.append(line)
        elif line.startswith("### "):
            flush()
            parts.append(f"<h2>{inline(line[4:].strip())}</h2>")
        elif re.match(r"^\s*[-*] ", line):
            if para or table:
                flush()
            items.append(re.sub(r"^\s*[-*] ", "", line).strip())
        else:
            if items or table:
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
    <dc:date>{date[:10]}</dc:date>
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



# ---------------------------------------------------------------- web

WEB_DIR = ROOT / "web"

WEB_CSS = """
:root { --bg:#fbfaf7; --fg:#1d1c1a; --muted:#6b6862; --line:#dedad2; --accent:#7a4b1e; --card:#ffffff; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#161513; --fg:#e8e5df; --muted:#9a968e; --line:#33312d; --accent:#e0a868; --card:#1e1d1a; }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin:0; background:var(--bg); color:var(--fg);
  font: 18px/1.6 Georgia, "Iowan Old Style", "Times New Roman", serif; }
main { max-width: 42rem; margin: 0 auto; padding: 1.5rem 1rem 4rem; }
nav.top { font: 14px/1.4 system-ui, sans-serif; margin-bottom: 1.5rem; display:flex; gap:1rem; flex-wrap:wrap; }
nav.top a, .toc a { color: var(--accent); text-decoration: none; }
nav.top a:hover, .toc a:hover { text-decoration: underline; }
h1 { font-size: 1.7rem; line-height: 1.25; margin: 0 0 0.6rem; }
h2 { font-size: 1.35rem; margin: 2.6rem 0 0.8rem; padding-top: 0.6rem; border-top: 2px solid var(--fg); }
h3 { font-size: 1.1rem; margin: 1.8rem 0 0.4rem; }
p { margin: 0 0 0.9rem; }
.intro { font-style: italic; color: var(--muted); }
.src { font: 13px/1.5 system-ui, sans-serif; color: var(--muted); }
.src a { color: var(--muted); }
a { color: var(--accent); }
ul { padding-left: 1.2rem; }
li { margin-bottom: 0.35rem; }
.toc { font: 15px/1.5 system-ui, sans-serif; background: var(--card); border:1px solid var(--line);
  border-radius: 8px; padding: 0.8rem 1rem; margin: 1.2rem 0 0; }
.toc ol { margin: 0.3rem 0 0; padding-left: 1.3rem; }
.tablewrap { overflow-x: auto; margin: 0.4rem 0 1.2rem; }
table { border-collapse: collapse; width: 100%; font: 14px/1.4 system-ui, sans-serif; }
th, td { border: 1px solid var(--line); padding: 0.35rem 0.5rem; text-align: left; vertical-align: top; }
th { background: var(--card); }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
footer { font: 13px/1.5 system-ui, sans-serif; color: var(--muted); margin-top: 3rem; }
"""


def web_page(title, body, back="index.html"):
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>{WEB_CSS}</style>
</head><body><main>
{body}
</main></body></html>
"""


def build_web(date: str, title: str, intro, sections, out: Path):
    """Versión web: una sola página con índice y anclas por sección."""
    toc = "".join(f'<li><a href="#s{n}">{html.escape(s["title"])}</a></li>'
                  for n, s in enumerate(sections, 1))
    parts = [
        f'<nav class="top"><a href="../index.html">← Todas las ediciones</a>'
        f'<a href="../epub/{date}.epub">Descargar EPUB</a></nav>',
        f"<h1>{html.escape(title)}</h1>",
    ]
    intro_html = blocks_to_html(intro)
    if intro_html:
        parts.append(f'<div class="intro">{intro_html}</div>')
    parts.append(f'<div class="toc"><strong>Secciones</strong><ol>{toc}</ol></div>')
    for n, sec in enumerate(sections, 1):
        body = blocks_to_html(sec["lines"]).replace("<h2>", "<h3>").replace("</h2>", "</h3>")
        body = body.replace("<table>", '<div class="tablewrap"><table>').replace("</table>", "</table></div>")
        parts.append(f'<section id="s{n}"><h2>{html.escape(sec["title"])}</h2>\n{body}</section>')
    parts.append('<footer><a href="#">↑ Volver arriba</a> · <a href="../index.html">Todas las ediciones</a></footer>')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(web_page(title, "\n".join(parts)), encoding="utf-8")


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

    rows = []
    for d in sorted(index, reverse=True):
        t = html.escape(index[d]["title"])
        if (WEB_DIR / f"{d}.html").exists():
            rows.append(f'<li><a class="t" href="web/{d}.html">{t}</a>'
                        f'<span class="f"><a href="web/{d}.html">Leer en la web</a> · '
                        f'<a href="epub/{d}.epub">EPUB</a></span></li>')
        else:
            rows.append(f'<li><span class="t">{t}</span>'
                        f'<span class="f"><a href="epub/{d}.epub">EPUB</a></span></li>')
    body = f"""<h1>{html.escape(FEED_TITLE)}</h1>
<p class="intro">Resumen diario de noticias. Cada edición se puede leer en el navegador o descargar en EPUB.</p>
<ul class="list">{"".join(rows)}</ul>
<footer>Catálogo OPDS para KOReader: <code>{BASE_URL}/opds.xml</code></footer>"""
    extra = """<style>
.list { list-style:none; padding:0; margin:1.5rem 0 0; }
.list li { padding:0.8rem 0; border-bottom:1px solid var(--line); margin:0; }
.list .t { display:block; font-size:1.05rem; color:var(--fg); text-decoration:none; }
.list a.t:hover { text-decoration:underline; }
.list .f { font: 14px/1.5 system-ui, sans-serif; color:var(--muted); }
code { font-size: 0.85em; word-break: break-all; }
</style>"""
    page = web_page(FEED_TITLE, body).replace("</head>", extra + "</head>")
    (ROOT / "index.html").write_text(page, encoding="utf-8")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1]).resolve()
    date = src.stem  # clave: AAAA-MM-DD o AAAA-MM-DD-tema
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}(-[a-z0-9]+(-[a-z0-9]+)*)?", date):
        sys.exit("El archivo tiene que llamarse AAAA-MM-DD.md o AAAA-MM-DD-tema.md "
                 "(tema en minúsculas, sin acentos, con guiones)")

    title, intro, sections = parse_edition(src.read_text(encoding="utf-8"))
    build_epub(date, title, intro, sections, EPUB_DIR / f"{date}.epub")
    build_web(date, title, intro, sections, WEB_DIR / f"{date}.html")

    index = json.loads(INDEX_JSON.read_text(encoding="utf-8")) if INDEX_JSON.exists() else {}
    index[date] = {
        "title": title,
        "summary": "Secciones: " + " · ".join(s["title"] for s in sections),
        "updated": dt.datetime.now(ART).isoformat(timespec="seconds"),
    }

    # conservar solo lo de los últimos KEEP días
    cutoff = (dt.datetime.now(ART).date() - dt.timedelta(days=KEEP)).isoformat()
    for old in [k for k in index if k[:10] < cutoff]:
        index.pop(old)
        (EPUB_DIR / f"{old}.epub").unlink(missing_ok=True)
        (WEB_DIR / f"{old}.html").unlink(missing_ok=True)
        (SRC_DIR / f"{old}.md").unlink(missing_ok=True)

    INDEX_JSON.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    write_catalog(index)
    (ROOT / ".nojekyll").touch()
    print(f"OK: epub/{date}.epub + web/{date}.html — {len(sections)} secciones — {len(index)} ediciones en el catálogo")


if __name__ == "__main__":
    main()
