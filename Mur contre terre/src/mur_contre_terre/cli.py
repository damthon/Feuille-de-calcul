"""Point d'entrée en ligne de commande — argparse (§3 du plan de conception).

Sans sous-commande, lance l'interface de bureau (``interface/bureau.py``,
importée localement pour ne pas rendre Tkinter obligatoire pour un usage
purement en ligne de commande). ``verifier`` calcule un projet ``.mct``
et écrit sa note de calcul (``rapport.generer_note_calcul``) sans
interface graphique — c'est aussi le point d'entrée de l'exécutable
empaqueté (lot 11, ``--autotest``).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

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
    p_verifier.add_argument("-o", "--sortie", help="Fichier Markdown de sortie (défaut : sortie standard)")

    # PyInstaller (lot 11) : vérifie l'exécutable sans afficher de fenêtre — un drapeau, pas une
    # sous-commande (une sous-commande ne peut pas commencer par "--", argparse la rejetterait).
    analyseur.add_argument("--autotest", action="store_true", help=argparse.SUPPRESS)

    return analyseur


def _verifier(fichier: str, sortie: str | None) -> int:
    try:
        projet = Projet.charger(fichier)
        resultat = calculer(projet)
        note = generer_note_calcul(projet, resultat)
    except (OSError, ValueError) as erreur:
        print(f"mur-contre-terre : {erreur}", file=sys.stderr)
        return 1
    if sortie:
        with open(sortie, "w", encoding="utf-8") as f:
            f.write(note)
    else:
        print(note)
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
