import pytest

from mur_contre_terre.donnees.sol import Sol, TypePoussee
from mur_contre_terre.unites import deg, kN_m3, MPa


def test_sol_minimal_valide():
    sol = Sol(gamma=kN_m3(18), phi=deg(30))
    assert sol.type_poussee is TypePoussee.ACTIF
    assert sol.niveau_nappe is None


def test_nappe_sans_gamma_sat_leve_une_erreur():
    with pytest.raises(ValueError):
        Sol(gamma=kN_m3(18), phi=deg(30), niveau_nappe=2.0)


def test_nappe_avec_gamma_sat_ok():
    sol = Sol(gamma=kN_m3(18), phi=deg(30), gamma_sat=kN_m3(20), niveau_nappe=2.0)
    assert sol.niveau_nappe == 2.0


def test_phi_hors_domaine_leve_une_erreur():
    with pytest.raises(ValueError):
        Sol(gamma=kN_m3(18), phi=0.0)
    with pytest.raises(ValueError):
        Sol(gamma=kN_m3(18), phi=deg(95))


def test_facteur_reduction_hors_domaine_leve_une_erreur():
    with pytest.raises(ValueError):
        Sol(gamma=kN_m3(18), phi=deg(30), facteur_reduction_ecoulement=1.2)


def test_ks_negatif_leve_une_erreur():
    with pytest.raises(ValueError):
        Sol(gamma=kN_m3(18), phi=deg(30), ks=-MPa(0.01))
