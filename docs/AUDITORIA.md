# Auditoría de la versión 0.1.0 (noviembre de 2026)

Revisión del código publicado en el commit `35a417b`, con evidencia obtenida al ejecutarlo sobre `data/ds024.pdf`.

## Defectos confirmados

| # | Impacto | Evidencia en la versión 0.1.0 | Corrección en la 0.2.0 |
|---|---|---|---|
| 1 | Alto: citas incorrectas | La consulta "EPP" mostraba "Artículo 81" con texto que pertenecía al final del artículo 80, sobre tesis de egresados (`docs/consulta_20260223_001102.txt`). "Derecho a negarse a trabajar" citaba el artículo 41 (prestaciones a víctimas de accidentes), cuando el derecho a retirarse está en el artículo 40. | El texto se divide por artículos antes de buscar; la cita y el texto siempre corresponden a la misma unidad. |
| 2 | Alto: texto derogado | El PDF consolidado contiene 60 artículos con su versión original seguida de la modificada (DS 023-2017-EM). La búsqueda podía citar la versión anterior. | Se conserva el texto vigente en el PDF y el original queda solo como referencia. |
| 3 | Alto: respuestas forzadas | `answer.py` recortaba cualquier respuesta para empezar en frases fijas ("retirarse de cualquier área de trabajo…"). Por eso "¿Qué indica sobre IPERC?" devolvía el derecho a retirarse. | Se eliminaron los recortes fijos; el fragmento mostrado es el que contiene más términos de la consulta. |
| 4 | Alto: causas inventadas | `accident.py` incluía siempre los mismos 5 porqués, la misma causa raíz y las mismas acciones con responsables y plazos, sin importar el evento. | El borrador deja esas secciones en blanco para el equipo investigador. Solo señala factores mencionados, para verificar. |
| 5 | Medio: falsos positivos | La detección buscaba fragmentos: "pare" coincidía con "parecía" y "separó", y "distr" con "distribución". Además, cada regla nueva sobrescribía a la anterior. | Expresiones de palabra completa; se informan todos los factores encontrados con las palabras que los activaron. |
| 6 | Medio: formulario | `/accidente` preguntaba dos veces por lesiones, daño y descripción, e ignoraba la segunda respuesta. No validaba fecha, lesiones ni tipo de daño. | Una sola pregunta por dato, con validación y coherencia entre lesiones y tipo de daño. |
| 7 | Medio: ranking | La puntuación contaba el término sin tildes dentro de un texto con tildes, por lo que valía 0 para palabras acentuadas. | BM25 sobre texto normalizado. |
| 8 | Medio: búsqueda | 1 de 30 preguntas de evaluación con el artículo correcto. | 20/30 en primera posición y 27/30 entre las tres primeras (ver README). |
| 9 | Bajo: repositorio | Se habían subido `__pycache__`, el historial y cuatro informes generados. `requirements.txt` estaba en UTF-16. | Se retiraron; los resultados van a `output/`, que está en `.gitignore`. `requirements.txt` está ahora en UTF-8. |
| 10 | Bajo: portabilidad | `/open-word` usaba `os.system("start …")`, que solo funciona en Windows, y las rutas dependían de la carpeta desde donde se ejecutaba. | Apertura según el sistema operativo y rutas relativas al proyecto. |
| 11 | Bajo: documentación | El README presentaba el proyecto como "AI platform", pero el código no usa modelos de IA. | El README describe lo que hace: búsqueda normativa con citas. |

## Vigencia de la norma

En el texto del reglamento, el PDF incluye las modificaciones del DS 023-2017-EM (el DS 029-2016-EM solo modificó una disposición del decreto aprobatorio). El DS 034-2023-EM (30-12-2023) modificó diversos artículos, entre ellos los de notificación de accidentes, e incorporó los artículos 418 a 423 y nueve anexos. Ese texto no está en el PDF. El programa lo advierte en cada respuesta y en cada borrador.

## Qué no se validó

- La exactitud de cada una de las 131 definiciones separadas automáticamente. Se revisaron las de uso frecuente.
- Que la reparación de palabras no haya unido ninguna pareja indebida. Se revisó una muestra y se comprobó que palabras frecuentes como "debajo", "sino" y "acerca" no aumentaron.
- El uso del borrador frente a los formatos internos de una unidad minera.
