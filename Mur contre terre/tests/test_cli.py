import json
from pathlib import Path

import pytest

from mur_contre_terre.cli import main
from mur_contre_terre.donnees.appuis import ConditionsAppui, TypeAppuiPied, TypeAppuiTete
from mur_contre_terre.donnees.charges import CasDeCharge, CategorieAction, TypeCharge
from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.donnees.materiaux import Acier, Beton, Materiaux
from mur_contre_terre.donnees.projet import Projet
from mur_contre_terre.donnees.sol import Sol
from mur_contre_terre.unites import deg, kN_m3


def _ecrire_projet(chemin: Path) -> None:
    projet = Projet(
        nom="Test CLI",
        geometrie=Geometrie(hauteur=2.0, ep_base=0.25, ep_couronnement=0.20, debord_semelle=0.6, ep_semelle=0.3),
        sol=Sol(gamma=kN_m3(18), phi=deg(30)),
        appuis=ConditionsAppui(pied=TypeAppuiPied.ENCASTREMENT, tete=TypeAppuiTete.LIBRE),
        materiaux=Materiaux(
            beton=Beton.depuis_classe("C30/37"), acier=Acier.b500b(), enrobage_terre=0.04, enrobage_interieur=0.04
        ),
        charges=(
            CasDeCharge(nom="Poids propre", type=TypeCharge.POIDS_PROPRE, categorie=CategorieAction.G, valeur=0.0),
        ),
        finesse_maillage=0.5,
    )
    projet.sauvegarder(chemin)


def test_verifier_ecrit_la_note_de_calcul_dans_un_fichier(tmp_path):
    projet_chemin = tmp_path / "projet.mct"
    _ecrire_projet(projet_chemin)
    sortie = tmp_path / "note.md"

    code = main(["verifier", str(projet_chemin), "-o", str(sortie)])

    assert code == 0
    assert sortie.exists()
    assert "Test CLI" in sortie.read_text(encoding="utf-8")


def test_verifier_affiche_sur_la_sortie_standard(tmp_path, capsys):
    projet_chemin = tmp_path / "projet.mct"
    _ecrire_projet(projet_chemin)

    code = main(["verifier", str(projet_chemin)])

    assert code == 0
    assert "Test CLI" in capsys.readouterr().out


def test_verifier_fichier_inexistant_renvoie_un_code_d_erreur(capsys):
    code = main(["verifier", "/chemin/inexistant.mct"])
    assert code == 1
    assert "mur-contre-terre" in capsys.readouterr().err


def test_verifier_fichier_mal_forme_renvoie_un_code_d_erreur(tmp_path, capsys):
    chemin = tmp_path / "invalide.mct"
    chemin.write_text(json.dumps({"format": 99, "projet": {}}), encoding="utf-8")

    code = main(["verifier", str(chemin)])

    assert code == 1
    assert capsys.readouterr().err


def test_verifier_exporte_en_pdf_selon_l_extension(tmp_path):
    projet_chemin = tmp_path / "projet.mct"
    _ecrire_projet(projet_chemin)
    sortie = tmp_path / "note.pdf"

    code = main(["verifier", str(projet_chemin), "-o", str(sortie)])

    assert code == 0
    assert sortie.read_bytes()[:5] == b"%PDF-"


def test_verifier_exporte_en_excel_selon_l_extension(tmp_path):
    projet_chemin = tmp_path / "projet.mct"
    _ecrire_projet(projet_chemin)
    sortie = tmp_path / "note.xlsx"

    code = main(["verifier", str(projet_chemin), "-o", str(sortie)])

    assert code == 0
    import openpyxl

    assert openpyxl.load_workbook(sortie).sheetnames == ["Données", "Combinaisons ELU", "Vérification de section"]
