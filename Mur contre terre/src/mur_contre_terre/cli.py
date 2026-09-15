"""Point d'entrée en ligne de commande — argparse (§3 du plan de conception).

Sans sous-commande, lance l'interface de bureau (``interface/bureau.py``,
importée localement pour ne pas rendre Tkinter obligatoire pour un usage
purement en ligne de commande). ``verifier`` calcule un projet ``.mct``
et écrit sa note de calcul sans interface graphique — au format déduit
de l'extension de ``--sortie`` (``.pdf``/``.xlsx`` via ``export.py``,
extra ``[export]`` ; Markdown par défaut, y compris sans ``--sortie``,
sur la sortie standard). C'est aussi le point d'entrée de l'exécutable
empaqueté (lot 11, ``--autotest``).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from mur_contre_terre.calcul import calculer
from mur_contre_terre.donnees.projet import Projet
from mur_contre_terre.rapport import generer_note_calcul


def _construire_analyseur() -> argparse.ArgumentParser:
    analyseur = argparse.ArgumentParser(
        prog="mur-contre-terre", description="Mur de sous-sol contre-terre — vérification SIA 260/261/262."
    )
    sous = analyseur.add_subparsers(dest="commande")

    p_verifier = sous.add_parser("verifier", help="Calcule un projet .mct et écrit sa note de calcul")
    p_verifier.add_argument("fichier", help="Fichier projet (.mct)")
    p_verifier.add_argument(
        "-o", "--sortie", help="Fichier de sortie — .md/.pdf/.xlsx selon l'extension (défaut : Markdown, sortie standard)"
    )

    # PyInstaller (lot 11) : vérifie l'exécutable sans afficher de fenêtre — un drapeau, pas une
    # sous-commande (une sous-commande ne peut pas commencer par "--", argparse la rejetterait).
    analyseur.add_argument("--autotest", action="store_true", help=argparse.SUPPRESS)

    return analyseur


def _verifier(fichier: str, sortie: str | None) -> int:
    try:
        projet = Projet.charger(fichier)
        resultat = calculer(projet)
    except (OSError, ValueError) as erreur:
        print(f"mur-contre-terre : {erreur}", file=sys.stderr)
        return 1

    extension = Path(sortie).suffix.lower() if sortie else ".md"
    try:
        if extension == ".pdf":
            from mur_contre_terre.export import exporter_pdf

            exporter_pdf(projet, resultat, sortie)
        elif extension == ".xlsx":
            from mur_contre_terre.export import exporter_excel

            exporter_excel(projet, resultat, sortie)
        elif sortie:
            Path(sortie).write_text(generer_note_calcul(projet, resultat), encoding="utf-8")
        else:
            print(generer_note_calcul(projet, resultat))
    except ImportError:
        print("mur-contre-terre : export PDF/Excel indisponible — installez l'extra [export]", file=sys.stderr)
        return 1
    return 0


def _autotest() -> int:
    """Vérifie que le paquet et ses imports différés (matplotlib Tk, Tkinter) sont bien présents."""
    import importlib

    importlib.import_module("mur_contre_terre.interface.bureau")

    print("mur-contre-terre : autotest OK (imports différés disponibles)")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _construire_analyseur().parse_args(argv)

    if args.autotest:
        return _autotest()
    if args.commande == "verifier":
        return _verifier(args.fichier, args.sortie)

    from mur_contre_terre.interface.bureau import lancer

    lancer()
    return 0


if __name__ == "__main__":
    sys.exit(main())
