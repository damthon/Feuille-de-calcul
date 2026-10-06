"""Convertit les PDF de normes en Markdown, en local, avec Marker.

    python outils/convertir_normes.py                  # normes_pdf/ -> normes_md/
    python outils/convertir_normes.py SRC DEST --ocr   # forcer l'OCR (PDF scannés)
    python outils/convertir_normes.py --force          # reconvertir même si le .md existe

Installation (une fois, dans un venv à chemin court sous Windows) :
    python -m venv C:\\mk && C:\\mk\\Scripts\\python.exe -m pip install marker-pdf
puis lancer ce script avec C:\\mk\\Scripts\\python.exe. Les PDF déjà convertis sont ignorés
(sauf --force). Les PDF les plus légers passent en premier ; la mise en veille
de Windows est bloquée pendant la conversion (écran allumé). Les PDF ajoutés en cours
de route sont aussi convertis.
"""

import argparse
import ctypes
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pypdfium2 as pdfium  # installé avec marker-pdf

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("source", nargs="?", default="normes_pdf", type=Path)
p.add_argument("dest", nargs="?", default="normes_md", type=Path)
p.add_argument("--ocr", action="store_true", help="forcer l'OCR sur tous les PDF")
p.add_argument("--force", action="store_true", help="reconvertir les PDF ayant déjà un .md (écrase)")
args = p.parse_args()

marker = shutil.which("marker_single") or shutil.which("marker_single", path=str(Path(sys.executable).parent))
if not marker:
    sys.exit("marker_single introuvable : pip install marker-pdf (voir l'en-tête du script)")


def a_faire():
    """Relu avant chaque PDF : les fichiers ajoutés pendant la conversion sont pris en compte."""
    pdfs = sorted(args.source.rglob("*.pdf"), key=lambda f: f.stat().st_size)
    return [f for f in pdfs if f not in vus and (args.force or not any((args.dest / f.stem).glob("*.md")))]


def redresser(pdf, dossier):
    """Copie sans pages tournées (/Rotate) : Marker les lit lettre par lettre (« P<br>a<br>g<br>e »).

    page_as_xobject applique déjà la rotation ; il suffit de poser chaque page sur une page neuve.
    Renvoie le PDF d'origine s'il n'a aucune page tournée.
    """
    src = pdfium.PdfDocument(pdf)
    if not any(page.get_rotation() for page in src):
        return pdf
    dst = pdfium.PdfDocument.new()
    for i, page in enumerate(src):
        neuve = dst.new_page(*page.get_size())
        neuve.insert_obj(src.page_as_xobject(i, dst).as_pageobject())
        neuve.gen_content()
    copie = Path(dossier) / pdf.name  # même nom : Marker nomme la sortie d'après le fichier
    dst.save(copie)
    return copie


if sys.platform == "win32":
    # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED : en veille moderne (S0), seul
    # « écran requis » empêche la mise en veille ; l'écran reste donc allumé pendant la conversion.
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000003)

vus, echecs = set(), []
while todo := a_faire():
    pdf = todo[0]
    vus.add(pdf)
    print(f"> {pdf.name} (reste {len(todo) - 1})")
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [marker, str(redresser(pdf, tmp)), "--output_dir", str(args.dest)] + (["--force_ocr"] if args.ocr else [])
        if subprocess.run(cmd).returncode:
            echecs.append(pdf.name)
            continue
    md = args.dest / pdf.stem / f"{pdf.stem}.md"
    md.write_text(md.read_text(encoding="utf-8").replace("<br>", " "), encoding="utf-8")  # retours à la ligne dans les cellules

print(f"\nTerminé : {len(vus) - len(echecs)}/{len(vus)} OK" + (f", échecs : {', '.join(echecs)}" if echecs else ""))
sys.exit(bool(echecs))
