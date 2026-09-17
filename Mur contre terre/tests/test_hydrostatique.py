import pytest

from mur_contre_terre.donnees.sol import Sol
from mur_contre_terre.geotechnique.hydrostatique import GAMMA_EAU, pression_hydrostatique
from mur_contre_terre.unites import deg, kN_m3


def test_pas_de_nappe_pression_nulle():
    sol = Sol(gamma=kN_m3(18), phi=deg(30))
    assert pression_hydrostatique(sol, hauteur=3.0, profondeur=3.0) == 0.0


def test_au_dessus_de_la_nappe_pression_nulle():
    # niveau_nappe=2.0 : plan d'eau à 2 m du pied, donc à une profondeur de 3.0-2.0=1.0 m sous la
    # surface — au-dessus de la nappe (profondeur=0.5 < 1.0), la pression est nulle.
    sol = Sol(gamma=kN_m3(18), phi=deg(30), gamma_sat=kN_m3(20), niveau_nappe=2.0)
    assert pression_hydrostatique(sol, hauteur=3.0, profondeur=0.5) == 0.0


def test_sous_la_nappe_triangulaire():
    # au pied (profondeur=3.0), on est à 3.0-1.0=2.0 m sous le plan d'eau (profondeur_nappe=1.0 m).
    sol = Sol(gamma=kN_m3(18), phi=deg(30), gamma_sat=kN_m3(20), niveau_nappe=2.0)
    assert pression_hydrostatique(sol, hauteur=3.0, profondeur=3.0) == pytest.approx(GAMMA_EAU * 2.0)


def test_facteur_de_reduction_ecoulement():
    sol = Sol(
        gamma=kN_m3(18), phi=deg(30), gamma_sat=kN_m3(20), niveau_nappe=2.0,
        facteur_reduction_ecoulement=0.7,
    )
    assert pression_hydrostatique(sol, hauteur=3.0, profondeur=3.0) == pytest.approx(0.7 * GAMMA_EAU * 2.0)


def test_niveau_nappe_est_mesure_depuis_le_pied_pas_depuis_la_surface():
    """Régression : Sol.niveau_nappe est la hauteur du plan d'eau depuis le pied du mur (label de
    l'onglet Sol et schéma), pas une profondeur depuis la surface — les deux ne coïncident que si
    niveau_nappe == hauteur/2."""
    sol = Sol(gamma=kN_m3(18), phi=deg(30), gamma_sat=kN_m3(20), niveau_nappe=2.5)
    # plan d'eau à 2.5 m du pied dans un mur de 3 m : seuls les 0.5 m du haut restent secs.
    assert pression_hydrostatique(sol, hauteur=3.0, profondeur=0.3) == 0.0  # 0.3 m sous la surface : encore sec
    assert pression_hydrostatique(sol, hauteur=3.0, profondeur=3.0) == pytest.approx(GAMMA_EAU * 2.5)  # au pied
