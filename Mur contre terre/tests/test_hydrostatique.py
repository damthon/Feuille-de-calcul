import pytest

from mur_contre_terre.donnees.sol import Sol
from mur_contre_terre.geotechnique.hydrostatique import GAMMA_EAU, pression_hydrostatique
from mur_contre_terre.unites import deg, kN_m3


def test_pas_de_nappe_pression_nulle():
    sol = Sol(gamma=kN_m3(18), phi=deg(30))
    assert pression_hydrostatique(sol, profondeur=3.0) == 0.0


def test_au_dessus_de_la_nappe_pression_nulle():
    sol = Sol(gamma=kN_m3(18), phi=deg(30), gamma_sat=kN_m3(20), niveau_nappe=2.0)
    assert pression_hydrostatique(sol, profondeur=1.0) == 0.0


def test_sous_la_nappe_triangulaire():
    sol = Sol(gamma=kN_m3(18), phi=deg(30), gamma_sat=kN_m3(20), niveau_nappe=2.0)
    assert pression_hydrostatique(sol, profondeur=3.0) == pytest.approx(GAMMA_EAU * 1.0)


def test_facteur_de_reduction_ecoulement():
    sol = Sol(
        gamma=kN_m3(18), phi=deg(30), gamma_sat=kN_m3(20), niveau_nappe=2.0,
        facteur_reduction_ecoulement=0.7,
    )
    assert pression_hydrostatique(sol, profondeur=3.0) == pytest.approx(0.7 * GAMMA_EAU * 1.0)
