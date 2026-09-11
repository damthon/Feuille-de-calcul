import pytest

from mur_contre_terre.donnees.appuis import ConditionsAppui, TypeAppuiPied, TypeAppuiTete
from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.donnees.sol import Sol
from mur_contre_terre.mecanique.appuis import dofs_bloques, rigidite_ressort_pied
from mur_contre_terre.mecanique.maillage import Maillage
from mur_contre_terre.unites import deg, kN_m3, MPa

_MAILLAGE = Maillage((0.0, 1.0, 2.0, 3.0))  # 4 nœuds, dernier = nœud 3


def test_dofs_bloques_encastrement_parfait_tete_libre():
    appuis = ConditionsAppui(pied=TypeAppuiPied.ENCASTREMENT, tete=TypeAppuiTete.LIBRE)
    assert dofs_bloques(appuis, _MAILLAGE) == [0, 1, 2]


def test_dofs_bloques_encastrement_parfait_tete_appuyee():
    appuis = ConditionsAppui(pied=TypeAppuiPied.ENCASTREMENT, tete=TypeAppuiTete.APPUI_DALLE)
    # nœud tête = 3 -> dof u = 3*3+1 = 10
    assert dofs_bloques(appuis, _MAILLAGE) == [0, 1, 2, 10]


def test_dofs_bloques_ressort_ne_bloque_pas_la_rotation_au_pied():
    appuis = ConditionsAppui(pied=TypeAppuiPied.RESSORT, tete=TypeAppuiTete.LIBRE, k_theta=1e6)
    assert dofs_bloques(appuis, _MAILLAGE) == [0, 1]


def test_rigidite_ressort_pied_none_si_encastrement_parfait():
    appuis = ConditionsAppui(pied=TypeAppuiPied.ENCASTREMENT)
    sol = Sol(gamma=kN_m3(18), phi=deg(30))
    g = Geometrie(hauteur=3.0, ep_base=0.30, ep_couronnement=0.20, debord_semelle=0.8, ep_semelle=0.4)
    assert rigidite_ressort_pied(appuis, sol, g) is None


def test_rigidite_ressort_pied_utilise_k_theta_saisi():
    appuis = ConditionsAppui(pied=TypeAppuiPied.RESSORT, k_theta=42.0)
    sol = Sol(gamma=kN_m3(18), phi=deg(30))
    g = Geometrie(hauteur=3.0, ep_base=0.30, ep_couronnement=0.20, debord_semelle=0.8, ep_semelle=0.4)
    assert rigidite_ressort_pied(appuis, sol, g) == 42.0


def test_rigidite_ressort_pied_calculee_depuis_ks_et_geometrie():
    appuis = ConditionsAppui(pied=TypeAppuiPied.RESSORT)
    sol = Sol(gamma=kN_m3(18), phi=deg(30), ks=MPa(0.03))
    g = Geometrie(hauteur=3.0, ep_base=0.30, ep_couronnement=0.20, debord_semelle=0.8, ep_semelle=0.4)
    attendu = MPa(0.03) * g.largeur_semelle**3 / 12.0
    assert rigidite_ressort_pied(appuis, sol, g) == pytest.approx(attendu)


def test_rigidite_ressort_pied_sans_ks_ni_k_theta_leve_une_erreur():
    appuis = ConditionsAppui(pied=TypeAppuiPied.RESSORT)
    sol = Sol(gamma=kN_m3(18), phi=deg(30))
    g = Geometrie(hauteur=3.0, ep_base=0.30, ep_couronnement=0.20, debord_semelle=0.8, ep_semelle=0.4)
    with pytest.raises(ValueError):
        rigidite_ressort_pied(appuis, sol, g)
