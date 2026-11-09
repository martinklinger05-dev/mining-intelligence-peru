# Mining Intelligence Peru (MIP)
[![Tests](https://github.com/martinklinger05-dev/mining-intelligence-peru/actions/workflows/tests.yml/badge.svg)](https://github.com/martinklinger05-dev/mining-intelligence-peru/actions/workflows/tests.yml)

Proyecto de Martin Klinger · Ingeniería de Minas, Universidad Católica de Santa María (Arequipa).

Herramienta de consola en Python para consultar el **Reglamento de Seguridad y Salud Ocupacional en Minería (DS 024-2016-EM)** con citas exactas, y para preparar el **borrador inicial de una investigación de incidentes o accidentes** con la normativa relacionada.

Es un buscador normativo (BM25), no un modelo de lenguaje: cada resultado es texto literal del reglamento con su ubicación (Título, Capítulo, Subcapítulo, Artículo) y su estado de modificación. No interpreta la norma ni reemplaza la revisión de un profesional.

> **Vigencia del texto.** El PDF incluido es el texto consolidado con las modificaciones del DS 023-2017-EM (agosto de 2017). **No incluye el DS 034-2023-EM** (publicado el 30-12-2023), que modificó, entre otros temas, la notificación de accidentes, ni normas posteriores. El programa muestra este aviso en cada respuesta. Antes de aplicar un artículo, verifíquelo en la publicación oficial.

## Qué hace

**1. Consulta con cita completa**

```
> ¿En cuánto tiempo se debe notificar un accidente mortal?

[1] DS 024-2016-EM, Título TERCERO, Capítulo XIX (Notificación e investigación de incidentes, …), Artículo 164
    Estado: Modificado por DS N° 023-2017-EM (18 agosto 2017). Se muestra el texto modificado.
    Los incidentes peligrosos y/o situaciones de emergencia y accidentes mortales, deben ser notificados
    por el titular de actividad minera, dentro de las veinticuatro (24) horas de ocurridos, …
```

- Devuelve los 3 artículos, definiciones o anexos más relacionados; `/ver N` muestra el texto completo.
- Entiende siglas del sector (EPP, IPERC, PETAR, PETS, ATS) y preguntas del tipo "¿qué es…?".
- Si un artículo fue modificado, muestra el texto vigente en el PDF y conserva el anterior como referencia.

**2. Borrador para iniciar una investigación** (`/accidente`)

A partir de los datos del evento (equipo, labor, turno, fecha, lesiones, daño y descripción), genera:

1. Clasificación preliminar según las definiciones del reglamento (accidente de trabajo, incidente o incidente peligroso).
2. Posibles factores mencionados en la descripción (humedad, rampa, señal de PARE, fatiga, etc.), indicados **para verificar** y no como causas.
3. Artículos relacionados con cada factor.
4. Artículos del capítulo de notificación e investigación.
5. Secciones en blanco para el equipo investigador: causas inmediatas, causas básicas, 5 porqués y acciones correctivas con responsable y plazo.

`/word` lo exporta a un documento Word con tablas para completar. El programa **no determina causas**: eso corresponde a la investigación en campo.

## Instalación y uso

Requiere Python 3.10 o superior. Desde la carpeta del proyecto:

```bash
python -m pip install -r requirements.txt
python -m app.main                                   # consola interactiva
python -m app.main "¿Qué trabajos requieren PETAR?"  # una consulta y termina
```

Comandos de la consola: una pregunta para buscar, `/ver N`, `/accidente`, `/word`, `/abrir`, `/exportar`, `/historial`, `/ayuda` y `/salir`. Las consultas y los documentos generados se guardan en `output/`, que no se sube a GitHub.

## Cómo funciona

1. **Lectura del PDF** (`app/regulation.py`, se ejecuta con `python -m app.build_index`). Divide el texto en 417 artículos, 131 definiciones del artículo 7 y 3 anexos, y guarda el resultado en `data/ds024_index.json`.
   - Detecta las notas *"(\*) Artículo modificado por…"* y se queda con el texto vigente.
   - Asigna a cada artículo su Título, Capítulo y Subcapítulo.
   - Repara 2198 palabras partidas por la extracción del PDF ("m ineras" → "mineras"). Solo las une si la palabra completa aparece intacta en el mismo documento y una de las piezas es un fragmento, de modo que "de bajo riesgo" no se convierte en "debajo riesgo".
2. **Búsqueda** (`app/search.py`). Usa BM25 por artículo, con normalización de tildes y reducción de sufijos ("notificar" y "notificados" coinciden). Da más peso al nombre del capítulo, a la primera oración del artículo y al término definido. Para palabras que siguen partidas, busca también en el texto sin espacios.
3. **Borrador de investigación** (`app/accident.py`, `app/word_export.py`). Detecta factores con expresiones de palabra completa y consulta el reglamento con el vocabulario de cada factor.

## Evaluación

`tests/eval_questions.json` contiene 30 preguntas redactadas como las haría un trabajador o estudiante. Para cada una, las respuestas aceptables se verificaron leyendo el artículo en el PDF. Las preguntas están divididas en dos grupos fijados antes de ejecutar el buscador: *dev* (para ajustar sinónimos y pesos) y *test* (sin ajustes).

| Versión | dev hit@1 | test hit@1 | test hit@3 | total hit@1 | total hit@3 |
|---|---:|---:|---:|---:|---:|
| Anterior (búsqueda por coincidencia de texto) | 0/15 | 1/15 | — | 1/30 | — |
| Actual (BM25 por artículo) | 12/15 | 8/15 | 14/15 | 20/30 | 27/30 |

*hit@1*: el primer resultado es correcto. *hit@3*: hay un resultado correcto entre los tres primeros. La versión anterior devolvía un solo artículo. La diferencia entre *dev* y *test* en hit@1 muestra el efecto del ajuste: el dato representativo es el de *test*. El conjunto es pequeño y lo elaboró el mismo autor; sirve para detectar regresiones, no como medida general de calidad. Para reproducirlo: `python -m app.evaluate --detail`.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Las 19 pruebas cubren:
- Reparación de palabras partidas y lectura de artículos modificados y definiciones.
- Que los 417 artículos aparezcan una sola vez y que el índice coincida con el PDF.
- Que no queden notas de modificación en el texto vigente.
- Ortografía flexible y siglas en la búsqueda, y que la evaluación no empeore.
- Validación de datos del formulario y que el borrador no invente causas.
- Exportación a Word e historial.

GitHub Actions las ejecuta con Python 3.10, 3.12 y 3.13.

## Archivos

| Archivo | Contenido |
|---|---|
| `app/regulation.py` | Lectura del PDF: artículos, modificaciones, definiciones, anexos y reparación de palabras |
| `app/search.py` | Búsqueda BM25, siglas y fragmento de evidencia |
| `app/answer.py` | Formato de citas y estado de modificación |
| `app/accident.py` | Borrador de investigación |
| `app/word_export.py` | Exportación a Word |
| `app/cli.py`, `app/main.py` | Consola |
| `app/evaluate.py` | Evaluación con preguntas verificadas |
| `data/ds024.pdf` | Texto consolidado del reglamento (fuente) |
| `data/ds024_index.json` | Índice generado a partir del PDF |
| `docs/AUDITORIA.md` | Problemas encontrados en la versión anterior y correcciones |

## Limitaciones

- El texto no incluye el DS 034-2023-EM ni modificaciones posteriores (ver aviso al inicio).
- El PDF solo trae los anexos 1, 2 y 3; los formatos (por ejemplo, el Anexo 21 de notificación) no están incluidos.
- La búsqueda es léxica: si la pregunta usa palabras muy distintas a las del reglamento, puede no encontrar el artículo. La tabla de siglas y sinónimos es corta.
- El artículo 7 se divide en definiciones de forma automática; algunas definiciones modificadas aparecen con su nombre original y el nuevo.
- El borrador de investigación no reemplaza los formatos y procedimientos internos de cada unidad minera.

## Siguiente fase

Mantener el texto actualizado con el DS 034-2023-EM, añadir los anexos de formatos y ampliar el conjunto de evaluación con preguntas reales de supervisores y trabajadores.
