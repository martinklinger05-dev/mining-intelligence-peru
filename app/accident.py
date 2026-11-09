"""Borrador estructurado para iniciar la investigación de un incidente o accidente.

El borrador NO determina causas. Ordena los datos ingresados, propone la clasificación que
corresponde según las definiciones del reglamento, señala posibles factores mencionados en la
descripción (para verificar) y cita los artículos aplicables. Las causas, los 5 porqués y las
acciones correctivas quedan en blanco para el equipo investigador, como exige el artículo que
asigna la investigación a la supervisión del área.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from app import VALIDITY_NOTICE
from app.answer import citation
from app.regulation import Unit, normalize
from app.search import Index

INJURY_OPTIONS = {"si": True, "sí": True, "no": False}
DAMAGE_OPTIONS = ("material", "personal", "ambos", "ninguno")

# Palabras que sugieren factores a verificar. Se buscan como palabras completas.
FACTORS = [
    # (clave, etiqueta, patrón en la descripción, consulta al reglamento)
    ("superficie", "Condición de la vía: humedad, barro o material suelto", r"humed\w*|mojad\w*|barro|lodo|resbal\w*|material suelto", "vías de circulación de vehículos en interior mina"),
    ("pendiente", "Tramo en pendiente o rampa", r"pendiente\w*|rampa\w*", "rampas pendiente vías"),
    ("curva", "Curva o intersección", r"curva\w*|interseccion\w*|cruce\w*|bocamina|by pass|bypass", "vías de circulación de vehículos en interior mina"),
    ("velocidad", "Velocidad de circulación", r"velocidad\w*|rapido|rapida", "velocidad máxima de vehículos en vías subterráneas"),
    ("senal", "Señalización o reglas de tránsito (PARE, preferencia)", r"pare|stop|senal\w*|preferencia", "vías de circulación de vehículos en interior mina"),
    ("visibilidad", "Visibilidad o iluminación", r"visibilidad|ilumin\w*|oscur\w*|encandil\w*|polvo|neblina", "iluminación de labores"),
    ("equipo", "Estado mecánico del equipo (frenos, dirección, neumáticos)", r"fren\w*|direccion|neumatic\w*|llanta\w*|falla mecanica|desperfecto", "frenos del vehículo"),
    ("acarreo", "Equipo de acarreo o transporte", r"volquete\w*|camion\w*|scoop\w*|lhd|dumper\w*|locomotora\w*|camioneta\w*", "equipo de acarreo transporte minería subterránea"),
    ("bloqueo", "Aislamiento de energía (bloqueo y tarjeteo)", r"bloqueo|candado\w*|tarjeta\w*|energizad\w*|energia", "bloqueo de energía"),
    ("epp", "Equipo de protección personal", r"epp|casco|guantes|arnes|lentes|respirador\w*|proteccion personal", "uso de equipo de protección personal"),
    ("gases", "Atmósfera: gases o ventilación", r"gas|gases|monoxido|ventilacion|oxigeno|humos", "monóxido de carbono ventilación"),
    ("roca", "Caída o desprendimiento de rocas, sostenimiento", r"desprendimiento|caida de roca\w*|planchon\w*|desatado|sostenimiento|shotcrete", "desprendimiento de rocas sostenimiento"),
    ("altura", "Trabajo en altura", r"altura|andamio\w*|escalera\w*|caida a distinto nivel", "trabajo en altura arnés"),
    ("fatiga", "Fatiga, horario o condición del trabajador", r"fatiga\w*|cansad\w*|sueno|somnolencia", "fatiga conductor horas de trabajo"),
    ("procedimiento", "Procedimiento, PETS o PETAR", r"pets|petar|procedimiento\w*|permiso\w*|ats", "procedimientos escritos de trabajo seguro"),
]


@dataclass
class EventInput:
    equipo: str
    area: str
    turno: str
    fecha_evento: str
    lesiones: bool
    danio: str
    descripcion: str

    def __post_init__(self):
        if not self.descripcion.strip():
            raise ValueError("La descripción del evento es obligatoria")
        if self.danio not in DAMAGE_OPTIONS:
            raise ValueError(f"Tipo de daño inválido: use {', '.join(DAMAGE_OPTIONS)}")
        if self.lesiones and self.danio in ("material", "ninguno"):
            raise ValueError("Si hubo lesiones, el tipo de daño debe ser 'personal' o 'ambos'")
        if not self.lesiones and self.danio in ("personal", "ambos"):
            raise ValueError("Si el daño es personal, indique que hubo lesiones")
        try:
            datetime.strptime(self.fecha_evento, "%Y-%m-%d %H:%M")
        except ValueError:
            raise ValueError("Fecha inválida: use AAAA-MM-DD HH:MM")


@dataclass
class Report:
    created: str
    event: EventInput
    classification: str
    classification_basis: list[str]
    factors: list[dict]
    regulations: list[dict]
    procedure: list[dict]
    notice: str = VALIDITY_NOTICE
    pending: list[str] = field(default_factory=lambda: [
        "Causas inmediatas (actos y condiciones subestándar), verificadas en campo",
        "Causas básicas (factores personales y del trabajo)",
        "Análisis de causa raíz (5 porqués u otro método) con evidencias",
        "Acciones correctivas y preventivas con responsable y plazo",
    ])


def detect_factors(description: str) -> list[dict]:
    text = normalize(description)
    found = []
    for key, label, pattern, query in FACTORS:
        words = sorted({m.group(0) for m in re.finditer(rf"\b(?:{pattern})\b", text)})
        if words:
            found.append({"key": key, "label": label, "evidence": words, "query": query})
    return found


def _definition(index: Index, term_start: str) -> Unit | None:
    return next((u for u in index.units if u.kind == "definicion" and normalize(u.term).startswith(term_start)), None)


def classify(event: EventInput, index: Index) -> tuple[str, list[str]]:
    if event.lesiones:
        unit = _definition(index, "accidente de trabajo")
        label = "Accidente de trabajo (con lesión). Determinar su gravedad (leve, incapacitante o mortal) según la definición."
    else:
        unit = _definition(index, "incidente")
        label = ("Incidente (sin lesiones). Si el evento pudo causar lesiones graves, invalidez o muerte, "
                 "evaluar si corresponde a incidente peligroso.")
    basis = [citation(u) for u in (unit, _definition(index, "incidente peligroso")) if u]
    return label, basis


def build_report(event: EventInput, index: Index) -> Report:
    factors = detect_factors(event.descripcion)
    # Una consulta por factor detectado (vocabulario del reglamento), en el orden de los factores.
    by_unit: dict[str, dict] = {}
    for factor in factors:
        hits = [h for h in index.search(factor["query"], k=4) if h.unit.kind != "definicion"]
        for hit in hits[:2]:
            entry = by_unit.setdefault(hit.unit.label, {"citation": citation(hit.unit), "passage": hit.passage, "factors": []})
            entry["factors"].append(factor["label"])
    regulations = list(by_unit.values())
    # Artículos del capítulo de notificación e investigación (sin números fijos en el código).
    procedure = [{"citation": citation(u), "summary": u.text[:300] + ("…" if len(u.text) > 300 else "")}
                 for u in index.units
                 if u.kind == "articulo" and u.chapter_name and "NOTIFICACI" in u.chapter_name.upper()
                 and "INVESTIGACI" in u.chapter_name.upper()]
    classification, basis = classify(event, index)
    return Report(datetime.now().strftime("%Y-%m-%d %H:%M"), event, classification, basis,
                  factors, regulations, procedure)


def report_text(r: Report) -> str:
    e = r.event
    lines = [
        "BORRADOR PARA INICIAR LA INVESTIGACIÓN — no constituye informe de investigación",
        f"Generado: {r.created}", "",
        "1. DATOS DEL EVENTO",
        f"   Equipo: {e.equipo}", f"   Área / labor: {e.area}", f"   Turno: {e.turno}",
        f"   Fecha y hora: {e.fecha_evento}", f"   Lesiones: {'sí' if e.lesiones else 'no'}",
        f"   Tipo de daño: {e.danio}", f"   Descripción: {e.descripcion}", "",
        "2. CLASIFICACIÓN PRELIMINAR", f"   {r.classification}",
        *[f"   Base: {b}" for b in r.classification_basis], "",
        "3. POSIBLES FACTORES MENCIONADOS EN LA DESCRIPCIÓN (verificar; no son causas)",
        *([f"   - {f['label']} (palabras: {', '.join(f['evidence'])})" for f in r.factors]
          or ["   - Ninguno detectado por palabras clave"]), "",
        "4. NORMATIVA RELACIONADA CON CADA FACTOR (búsqueda por relevancia; revisar aplicabilidad)",
        *([f"   - {x['citation']}\n     Relacionado con: {'; '.join(x['factors'])}\n     {x['passage']}" for x in r.regulations]
          or ["   - Sin factores detectados: consulte el reglamento con el buscador."]), "",
        "5. NOTIFICACIÓN E INVESTIGACIÓN: ARTÍCULOS APLICABLES",
        *[f"   - {x['citation']}" for x in r.procedure], "",
        "6. PENDIENTE PARA EL EQUIPO INVESTIGADOR",
        *[f"   - {p}" for p in r.pending], "",
        r.notice,
    ]
    return "\n".join(lines)
