# Noticias

Resumen diario de noticias en EPUB, publicado como catálogo OPDS para KOReader.

- Catálogo OPDS: <https://nahuellopezibb.github.io/Noticias/opds.xml>
- Página web: <https://nahuellopezibb.github.io/Noticias/>

## Cómo funciona

1. Una tarea programada de Claude se ejecuta todas las mañanas, sigue
   [`INSTRUCCIONES.md`](INSTRUCCIONES.md) y escribe la edición del día en
   `ediciones/AAAA-MM-DD.md`.
2. [`tools/build.py`](tools/build.py) convierte ese markdown en
   `epub/AAAA-MM-DD.epub`, regenera `opds.xml` e `index.html` y borra las
   ediciones de más de 14 días.
3. El push a `main` dispara GitHub Pages, que publica todo en un par de minutos.
4. En KOReader, el catálogo OPDS muestra las ediciones y las descarga con un toque.

## Estructura

| Ruta | Qué es |
| --- | --- |
| `INSTRUCCIONES.md` | Secciones, criterios y formato. Editalo para cambiar el contenido. |
| `ediciones/` | Fuente markdown de cada edición. |
| `epub/` | Los EPUB y `index.json` (metadatos para el catálogo). |
| `opds.xml` | Catálogo OPDS (Atom) que lee KOReader. |
| `tools/build.py` | Generador, solo biblioteca estándar de Python. |
| `.nojekyll` | Le indica a Pages que sirva los archivos tal cual. |

## Probar a mano

```bash
python3 tools/build.py ediciones/2026-10-25.md
```
