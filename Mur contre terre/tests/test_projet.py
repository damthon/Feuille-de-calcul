import math

import pytest

from mur_contre_terre.donnees.appuis import ConditionsAppui, TypeAppuiPied, TypeAppuiTete
from mur_contre_terre.donnees.charges import CasDeCharge, CategorieAction, TypeCharge
from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.donnees.materiaux import Acier, Beton, Materiaux
from mur_contre_terre.donnees.projet import Projet
from mur_contre_terre.donnees.sol import Sol, TypePoussee
from mur_contre_terre.unites import deg, kN, kN_m3, MPa


def _projet_exemple() -> Projet:
    return Projet(
        nom="Mur de sous-sol — exemple",
        geometrie=Geometrie(hauteur=3.0, ep_base=0.30, ep_couronnement=0.20, debord_semelle=0.80, ep_semelle=0.40),
        sol=Sol(
            gamma=kN_m3(18),
            phi=deg(30),
            c=0.0,
            delta=deg(20),
            gamma_sat=kN_m3(20),
            niveau_nappe=2.0,
            type_poussee=TypePoussee.ACTIF,
            ks=MPa(0.03),
        ),
        appuis=ConditionsAppui(pied=TypeAppuiPied.RESSORT, tete=TypeAppuiTete.APPUI_DALLE),
        materiaux=Materiaux(
            beton=Beton.depuis_classe("C30/37"),
            acier=Acier.b500b(),
            enrobage_terre=0.05,
            enrobage_interieur=0.04,
        ),
        charges=(
            CasDeCharge(
                nom="Charge en tête",
                type=TypeCharge.CHARGE_TETE,
                categorie=CategorieAction.G,
                valeur=kN(80),
                parametres={"excentricite": 0.05},
            ),
            CasDeCharge(
                nom="Surcharge terre-plein",
                type=TypeCharge.CHARGE_SURFACIQUE_TERREPLEIN,
                categorie=CategorieAction.Q,
                valeur=kN(5),
                psi0=0.7,
                psi1=0.5,
                psi2=0.3,
            ),
        ),
        finesse_maillage=0.25,
    )


def test_projet_valide_construit():
    p = _projet_exemple()
    assert len(p.charges) == 2
    assert math.isclose(p.geometrie.largeur_semelle, 1.10)


def test_finesse_maillage_superieure_a_la_hauteur_leve_une_erreur():
    p = _projet_exemple()
    with pytest.raises(ValueError):
        Projet(
            nom=p.nom, geometrie=p.geometrie, sol=p.sol, appuis=p.appuis, materiaux=p.materiaux,
            charges=p.charges, finesse_maillage=10.0,
        )


def test_ressort_sans_ks_ni_k_theta_leve_une_erreur():
    p = _projet_exemple()
    sol_sans_ks = Sol(gamma=p.sol.gamma, phi=p.sol.phi)
    with pytest.raises(ValueError):
        Projet(
            nom=p.nom, geometrie=p.geometrie, sol=sol_sans_ks, appuis=p.appuis, materiaux=p.materiaux,
            charges=p.charges,
        )


def test_pas_de_charge_par_defaut():
    p = _projet_exemple()
    assert p.pas_de_charge[0] == pytest.approx(0.05)
    assert p.pas_de_charge[-1] == pytest.approx(1.0)


def test_aller_retour_json(tmp_path):
    p = _projet_exemple()
    chemin = tmp_path / "exemple.mct"
    p.sauvegarder(chemin)

    relu = Projet.charger(chemin)

    assert relu.nom == p.nom
    assert relu.geometrie == p.geometrie
    assert relu.sol == p.sol
    assert relu.appuis == p.appuis
    assert relu.materiaux == p.materiaux
    assert relu.charges == p.charges
    assert relu.finesse_maillage == p.finesse_maillage
    assert relu.pas_de_charge == p.pas_de_charge
    assert relu == p


def test_fichier_projet_est_lisible(tmp_path):
    p = _projet_exemple()
    chemin = tmp_path / "exemple.mct"
    p.sauvegarder(chemin)

    contenu = chemin.read_text(encoding="utf-8")
    assert '"format": 1' in contenu
    assert "Mur de sous-sol" in contenu


def test_format_de_fichier_inconnu_leve_une_erreur(tmp_path):
    chemin = tmp_path / "invalide.mct"
    chemin.write_text('{"format": 99, "projet": {}}', encoding="utf-8")
    with pytest.raises(ValueError):
        Projet.charger(chemin)
