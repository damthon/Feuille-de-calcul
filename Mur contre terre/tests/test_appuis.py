import pytest

from mur_contre_terre.donnees.appuis import ConditionsAppui, TypeAppuiPied, TypeAppuiTete


def test_defauts():
    a = ConditionsAppui()
    assert a.pied is TypeAppuiPied.ENCASTREMENT
    assert a.tete is TypeAppuiTete.LIBRE
    assert a.k_theta is None


def test_ressort_avec_k_theta_saisi():
    a = ConditionsAppui(pied=TypeAppuiPied.RESSORT, k_theta=5.0e7)
    assert a.k_theta == 5.0e7


def test_k_theta_sur_encastrement_parfait_leve_une_erreur():
    with pytest.raises(ValueError):
        ConditionsAppui(pied=TypeAppuiPied.ENCASTREMENT, k_theta=5.0e7)


def test_k_theta_negatif_leve_une_erreur():
    with pytest.raises(ValueError):
        ConditionsAppui(pied=TypeAppuiPied.RESSORT, k_theta=-1.0)
