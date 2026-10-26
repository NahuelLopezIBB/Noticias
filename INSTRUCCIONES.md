# Instrucciones para armar la edición diaria

La tarea programada lee este archivo en cada ejecución. Para cambiar qué
noticias se buscan o cómo se escriben, editá este archivo: no hace falta tocar
la tarea.

## Secciones (en este orden)

1. **Argentina: política y economía.** Gobierno nacional, Congreso, provincias
   cuando tengan alcance nacional, justicia con impacto político. En economía:
   inflación, tipo de cambio, reservas, deuda, FMI, actividad, medidas oficiales.
2. **Geopolítica y conflictos.** Foco en Estados Unidos, la Unión Europea y
   China, y en las relaciones entre ellos. Conflictos armados en curso y su
   evolución. Fuera de esos ejes, solo lo de mayor peso.
3. **Ciencia y tecnología.** Avances científicos relevantes (publicaciones
   importantes, resultados de misiones, medicina, física, clima) y tecnología
   con impacto real (IA, semiconductores, energía, espacio). Nada de
   lanzamientos de productos de consumo ni rumores.
4. **Sector nuclear.** Prioridad a la Argentina: CNEA, NA-SA, INVAP, ARN,
   Atucha, Embalse, CAREM, RA-10, uranio, exportaciones, política nuclear.
   Después, lo internacional relevante: nuevos reactores, SMR, fusión,
   OIEA, combustible, seguridad.

## Criterios

- Noticias de las **últimas 24 horas**. En el sector nuclear se puede ampliar
  a la última semana si en el día no hay nada relevante, y hay que aclararlo.
- Entre **4 y 6 noticias por sección**, ordenadas de más a menos relevantes.
  Si una sección no tiene noticias de peso, se dice en una línea y no se
  rellena.
- Contrastar cada noticia con al menos dos fuentes cuando sea posible.
  Preferir fuentes primarias (comunicados oficiales, organismos, papers) y
  medios serios de distintas líneas editoriales.
- Tono informativo y neutral. En temas políticos, presentar los hechos y, si
  corresponde, las posiciones de cada parte, sin opinar.
- **Contexto cuando la noticia lo requiera.** Si una noticia es parte de una
  historia más larga (una causa judicial, una negociación, un conflicto, un
  proyecto de ley, una obra), agregar un párrafo de contexto antes o después
  de la novedad: qué es el caso o el tema, cómo empezó y cuáles fueron los
  últimos desarrollos previos a la noticia de hoy, con fechas. Buscar ese
  antecedente con la misma rigurosidad que la noticia. Ejemplo: ante el
  sobreseimiento de Javier y Karina Milei, explicar qué fue el caso $Libra
  (la promoción de la criptomoneda en febrero de 2025 y lo que pasó después)
  y qué había ocurrido en la causa en las semanas anteriores. No hace falta
  contexto en noticias autoexplicativas o de un solo hecho.
- No repetir noticias de la edición anterior salvo que haya novedades; en ese
  caso, contar lo nuevo con un breve recordatorio del contexto.
- Todo redactado con palabras propias: nada de copiar párrafos ni citas
  largas de los medios.

## Formato del archivo `ediciones/AAAA-MM-DD.md`

```
# Noticias del día — domingo 25 de octubre de 2026

Una o dos oraciones con lo más importante del día (opcional).

## Argentina: política y economía

### Título de la noticia

Uno o dos párrafos con qué pasó, por qué importa y qué sigue.

Fuentes: [Medio 1](https://...), [Medio 2](https://...)

### Otra noticia
...

## Geopolítica y conflictos
...
```

Reglas del formato:

- `# ` solo una vez, en la primera línea: es el título del libro.
- `## ` es cada sección (cada una queda como capítulo en el índice del Kindle).
- `### ` es cada noticia.
- La línea de fuentes empieza con `Fuentes:` y lleva links en markdown.
- Se pueden usar `**negrita**`, `*cursiva*` y listas con `- `.
- Tablas: se permiten en formato markdown (`| a | b |` con la fila `|---|---|`
  debajo del encabezado), pero la pantalla del Kindle es angosta. Máximo
  **4 columnas**, celdas cortas (números, nombres, fechas), sin texto largo.
  Si los datos no entran en ese formato, usar una lista con un elemento por
  fila, por ejemplo: `- **Lula:** 64,2 millones (51,78 %)`.

## Informes especiales

Los pedidos están en `PEDIDOS.md`. Si hay al menos uno en "Pendientes", tomar
**el primero** (uno por día) y agregarlo como **último capítulo** de la edición:

```
## Informe especial: <tema>

Introducción breve: de qué se trata y por qué importa.

### Antecedentes
### Situación actual
### Actores y posiciones
### Qué puede pasar / qué mirar

Fuentes: [...](https://...), [...](https://...)
```

- Los subtítulos son orientativos: adaptarlos al tema (para un tema científico
  o técnico pueden ser "Cómo funciona", "Estado del arte", "Desafíos").
- Extensión: entre 1.500 y 3.000 palabras. Profundidad de divulgación seria,
  para un lector con formación técnica (ingeniero nuclear). Usar datos, fechas
  y cifras concretas.
- Investigar a fondo: muchas más búsquedas que para una noticia, y priorizar
  fuentes primarias (documentos oficiales, informes de organismos, papers).
- Mismo criterio de neutralidad que las noticias. Si el pedido incluye
  aspectos específicos, cubrirlos todos.
- Al terminar, mover la línea del pedido de "Pendientes" a "Hechos", agregando
  la fecha de la edición al principio: `- AAAA-MM-DD: <pedido>`.
- Si la edición incluye un informe, mencionarlo al final del título del libro:
  `# Noticias del día — lunes 26 de octubre de 2026 · Informe: <tema corto>`.

## Informes a pedido (fuera del horario diario)

A veces Nahuel pide un informe para una hora puntual. Esos salen como **libro
aparte** en el catálogo, no dentro de la edición diaria:

- Archivo: `ediciones/AAAA-MM-DD-tema.md`, con el tema en minúsculas, sin
  acentos y con guiones (ej.: `2026-10-25-elecciones-brasil.md`).
- Primera línea: `# Informe especial: <tema> — <fecha>`.
- Cada parte del informe es un capítulo `## ` (Antecedentes, Situación actual,
  etc.), con `### ` para subtemas. Mismos criterios de extensión, profundidad,
  fuentes y neutralidad que los informes especiales de arriba.
- Generar con `python3 tools/build.py ediciones/AAAA-MM-DD-tema.md` y hacer
  commit y push con el mensaje `Informe AAAA-MM-DD-tema`.
- No tocar `PEDIDOS.md` ni la edición diaria.

## Pasos de cada ejecución

1. Calcular la fecha de hoy en hora argentina (UTC-3).
2. Leer la edición anterior en `ediciones/` para no repetir.
3. Revisar `PEDIDOS.md`.
4. Buscar las noticias de cada sección y, si hay pedido, investigar el informe.
5. Escribir `ediciones/AAAA-MM-DD.md` y, si hubo informe, actualizar `PEDIDOS.md`.
6. Ejecutar `python3 tools/build.py ediciones/AAAA-MM-DD.md`.
7. Hacer commit y push a `main` con el mensaje `Edición AAAA-MM-DD`.
