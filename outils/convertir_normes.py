"""Convertit les PDF de normes en Markdown, en local, avec Marker.

    python outils/convertir_normes.py                  # normes_pdf/ -> normes_md/
    python outils/convertir_normes.py SRC DEST --ocr   # forcer l'OCR (PDF scannés)

Installation (une fois, dans un venv à chemin court sous Windows) :
    python -m venv C:\\mk && C:\\mk\\Scripts\\python.exe -m pip install marker-pdf
puis lancer ce script avec C:\\mk\\Scripts\\python.exe. Les PDF déjà convertis sont ignorés.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("source", nargs="?", default="normes_pdf", type=Path)
p.add_argument("dest", nargs="?", default="normes_md", type=Path)
p.add_argument("--ocr", action="store_true", help="forcer l'OCR sur tous les PDF")
args = p.parse_args()

marker = shutil.which("marker_single") or shutil.which("marker_single", path=str(Path(sys.executable).parent))
if not marker:
    sys.exit("marker_single introuvable : pip install marker-pdf (voir l'en-tête du script)")
pdfs = sorted(args.source.rglob("*.pdf"))
if not pdfs:
    sys.exit(f"Aucun PDF dans {args.source}")

echecs = []
for pdf in pdfs:
    if (args.dest / pdf.stem / f"{pdf.stem}.md").exists():
        print(f"= {pdf.name} (déjà converti)")
        continue
    print(f"> {pdf.name}")
    cmd = [marker, str(pdf), "--output_dir", str(args.dest)] + (["--force_ocr"] if args.ocr else [])
    if subprocess.run(cmd).returncode:
        echecs.append(pdf.name)

print(f"\nTerminé : {len(pdfs) - len(echecs)}/{len(pdfs)} OK" + (f", échecs : {', '.join(echecs)}" if echecs else ""))
sys.exit(bool(echecs))
