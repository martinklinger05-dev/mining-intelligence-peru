"""Interfaz de consola de Mining Intelligence Peru."""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime

from app import VALIDITY_NOTICE, __version__
from app.accident import DAMAGE_OPTIONS, INJURY_OPTIONS, EventInput, build_report, report_text
from app.answer import format_hits, format_unit
from app.regulation import load_units
from app.search import Index
from app.storage import append_history, export_text, read_last_history

CANCEL = {"/cancelar", "cancelar", "/salir", "salir", "/exit", "exit"}
HELP = """
Comandos:
  (escriba una pregunta)   buscar en el reglamento, p. ej.: ¿Qué trabajos requieren PETAR?
  /ver N                   texto completo del resultado N de la última búsqueda
  /accidente               borrador para iniciar la investigación de un evento
  /word                    exportar el último borrador a Word (.docx)
  /abrir                   abrir el último Word exportado
  /exportar                guardar la última respuesta en un .txt
  /historial               últimas 10 consultas
  /ayuda                   esta ayuda
  /salir                   terminar
"""


class Cancelled(Exception):
    pass


def ask(label: str, validate=None, default: str | None = None) -> str:
    while True:
        value = input(label).strip()
        if value.lower() in CANCEL:
            raise Cancelled
        if not value and default is not None:
            value = default
        try:
            return validate(value) if validate else value
        except ValueError as exc:
            print(f"  {exc}. Intente de nuevo o escriba /cancelar.")


def _required(value: str) -> str:
    if not value:
        raise ValueError("Dato obligatorio")
    return value


def _injury(value: str) -> bool:
    if value.lower() not in INJURY_OPTIONS:
        raise ValueError("Responda si o no")
    return INJURY_OPTIONS[value.lower()]


def _damage(value: str) -> str:
    if value.lower() not in DAMAGE_OPTIONS:
        raise ValueError(f"Opciones: {', '.join(DAMAGE_OPTIONS)}")
    return value.lower()


def _date(value: str) -> str:
    datetime.strptime(value, "%Y-%m-%d %H:%M")
    return value


def accident_form() -> EventInput:
    print("\nBORRADOR DE INVESTIGACIÓN (escriba /cancelar para salir del formulario)")
    while True:
        event = dict(
            equipo=ask("Equipo (ej. Volquete 21): ", _required),
            area=ask("Área / labor (ej. NV 4300, Rampa 6000): ", _required),
            turno=ask("Turno (día/noche): ", _required),
            fecha_evento=ask("Fecha y hora (AAAA-MM-DD HH:MM) [Enter = ahora]: ", _date,
                             default=datetime.now().strftime("%Y-%m-%d %H:%M")),
            lesiones=ask("¿Hubo lesiones? (si/no): ", _injury),
            danio=ask(f"Tipo de daño ({'/'.join(DAMAGE_OPTIONS)}): ", _damage),
            descripcion=ask("Describa el evento (qué pasó, dónde, condiciones, maniobra): ", _required),
        )
        try:
            return EventInput(**event)
        except ValueError as exc:
            print(f"  {exc}. Revise los datos.")


def open_file(path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa: S606 (solo Windows)
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def run_cli() -> None:
    units, meta = load_units()
    index = Index(units)
    counts = meta["counts"]
    print(f"Mining Intelligence Peru v{__version__} — DS 024-2016-EM: {counts['articulos']} artículos, "
          f"{counts['definiciones']} definiciones, {counts['anexos']} anexos.")
    print(VALIDITY_NOTICE)
    print("Escriba /ayuda para ver los comandos.\n")
    last_hits, last_answer, last_report, last_word = [], None, None, None
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        cmd = line.lower()
        if cmd in ("/salir", "salir", "/exit", "exit"):
            break
        if cmd in ("/ayuda", "/help", "ayuda"):
            print(HELP)
        elif cmd.startswith("/ver"):
            try:
                print("\n" + format_unit(last_hits[int(cmd.split()[1]) - 1].unit) + "\n")
            except (IndexError, ValueError):
                print("Use /ver N después de una búsqueda (N = número del resultado).")
        elif cmd == "/historial":
            for item in read_last_history(10) or []:
                print(f"[{item['timestamp']}] {item['question']}  →  {', '.join(item.get('results', []))}")
        elif cmd == "/exportar":
            print(f"Guardado en {export_text(last_answer, 'consulta')}" if last_answer else "Aún no hay respuesta.")
        elif cmd == "/accidente":
            try:
                event = accident_form()
            except Cancelled:
                print("Formulario cancelado.\n")
                continue
            last_report = build_report(event, index)
            last_answer = report_text(last_report)
            print("\n" + last_answer + "\n\nUse /word para exportarlo a Word.\n")
            append_history({"timestamp": last_report.created, "question": f"/accidente: {event.descripcion[:80]}",
                            "results": [r["citation"].split(", ")[-1] for r in last_report.regulations]})
        elif cmd == "/word":
            if not last_report:
                print("Primero genere un borrador con /accidente.")
                continue
            from app.word_export import export_report_docx
            last_word = export_report_docx(last_report)
            print(f"Word guardado en {last_word}")
        elif cmd == "/abrir":
            open_file(last_word) if last_word else print("Primero exporte con /word.")
        elif cmd.startswith("/"):
            print("Comando no reconocido. Escriba /ayuda.")
        else:
            last_hits = index.search(line, k=3)
            last_answer = format_hits(line, last_hits)
            print("\n" + last_answer + "\n")
            append_history({"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "question": line,
                            "results": [h.unit.label for h in last_hits]})
    print("Hasta luego.")
