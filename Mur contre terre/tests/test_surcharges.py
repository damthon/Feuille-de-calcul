import math

import pytest

from mur_contre_terre.geotechnique.surcharges import pression_charge_lineaire, pression_charge_surfacique


def test_pression_charge_lineaire_nulle_en_surface():
    assert pression_charge_lineaire(intensite=50e3, distance=2.0, profondeur=0.0) == 0.0


def test_pression_charge_lineaire_maximum_en_z_egal_a_a_sur_racine_3():
    a = 2.0
    z_pic = a / math.sqrt(3)
    f = lambda z: pression_charge_lineaire(50e3, a, z)
    assert f(z_pic) > f(z_pic - 0.05)
    assert f(z_pic) > f(z_pic + 0.05)


def test_pression_charge_lineaire_decroit_avec_la_distance():
    proche = pression_charge_lineaire(50e3, distance=1.0, profondeur=1.0)
    loin = pression_charge_lineaire(50e3, distance=10.0, profondeur=1.0)
    assert proche > loin


def test_pression_charge_lineaire_domaine_invalide():
    with pytest.raises(ValueError):
        pression_charge_lineaire(50e3, distance=0.0, profondeur=1.0)
    with pytest.raises(ValueError):
        pression_charge_lineaire(50e3, distance=1.0, profondeur=-0.1)


def test_pression_charge_surfacique_converge_vers_la_charge_lineaire_pour_une_bande_etroite():
    q = 10e3  # Pa
    distance = 3.0
    eps = 1e-4
    surfacique = pression_charge_surfacique(q, distance, etendue=eps, profondeur=2.0)
    lineaire_equivalente = pression_charge_lineaire(q * eps, distance, profondeur=2.0)
    assert surfacique == pytest.approx(lineaire_equivalente, rel=1e-3)


def test_pression_charge_surfacique_distance_nulle_ne_leve_pas_d_erreur():
    assert pression_charge_surfacique(10e3, distance=0.0, etendue=2.0, profondeur=1.0) > 0.0


def test_pression_charge_surfacique_domaine_invalide():
    with pytest.raises(ValueError):
        pression_charge_surfacique(10e3, distance=-1.0, etendue=2.0, profondeur=1.0)
    with pytest.raises(ValueError):
        pression_charge_surfacique(10e3, distance=0.0, etendue=0.0, profondeur=1.0)
    with pytest.raises(ValueError):
        pression_charge_surfacique(10e3, distance=0.0, etendue=2.0, profondeur=-1.0)
