"""Punto de entrada.

  python -m app.main                       consola interactiva
  python -m app.main "¿Qué es el IPERC?"   una consulta y termina
"""
import sys

from app.answer import format_hits
from app.cli import run_cli
from app.regulation import load_units
from app.search import Index


def main() -> None:
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        units, _ = load_units()
        print(format_hits(query, Index(units).search(query, k=3)))
    else:
        run_cli()


if __name__ == "__main__":
    main()
