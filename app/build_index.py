"""Reconstruye data/ds024_index.json a partir de data/ds024.pdf.

Uso: python -m app.build_index
"""
import time

from app.regulation import INDEX_PATH, PDF_PATH, build_index


def main() -> None:
    start = time.time()
    data = build_index(PDF_PATH, INDEX_PATH)
    counts = data["counts"]
    print(f"Índice generado en {INDEX_PATH} ({time.time() - start:.1f} s)")
    print(f"  {counts['articulos']} artículos, {counts['definiciones']} definiciones, {counts['anexos']} anexos")
    print(f"  Modificaciones incluidas en el PDF: {', '.join(data['amendments_included']) or 'ninguna'}")
    print(f"  Palabras partidas reparadas: {data['word_repairs']}")


if __name__ == "__main__":
    main()
