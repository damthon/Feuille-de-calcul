"""Recoupement du solveur linéaire contre des solutions fermées de RDM.

Cantilever = mur encastré au pied, tête libre. Les valeurs attendues sont
les formules classiques de résistance des matériaux ; la convention de
signe de N/V/M est documentée et calibrée dans ``solveur_lineaire.py``.
"""

import numpy as np
import pytest

from mur_contre_terre.donnees.appuis import ConditionsAppui, TypeAppuiPied, TypeAppuiTete
from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.donnees.sol import Sol
from mur_contre_terre.mecanique.maillage import Maillage
from mur_contre_terre.mecanique.rigidite import assembler
from mur_contre_terre.mecanique.solveur_lineaire import resoudre
from mur_contre_terre.unites import deg, kN_m3

# Géométrie/sol passés à `resoudre` même quand ils ne servent pas (pied encastré) :
_GEOMETRIE = Geometrie(hauteur=3.0, ep_base=0.30, ep_couronnement=0.30, debord_semelle=0.8, ep_semelle=0.4)
_SOL = Sol(gamma=kN_m3(18), phi=deg(30))

_EA = 1.0e9  # grand, pour ne pas coupler avec la flexion dans les essais transversaux
_EI = 5000.0
_L_TOTAL = 3.0


def _maillage(n_elements: int) -> Maillage:
    pas = _L_TOTAL / n_elements
    return Maillage(tuple(i * pas for i in range(n_elements + 1)))


def test_console_charge_transversale_en_tete():
    m = _maillage(2)
    ea = [_EA] * m.nb_elements
    ei = [_EI] * m.nb_elements
    appuis = ConditionsAppui(pied=TypeAppuiPied.ENCASTREMENT, tete=TypeAppuiTete.LIBRE)
    P = 10.0
    F = np.zeros(m.nb_dof)
    F[3 * (m.nb_noeuds - 1) + 1] = P  # u au dernier nœud

    r = resoudre(m, ea, ei, appuis, _SOL, _GEOMETRIE, F)

    u_tete = r.deplacements[-1, 1]
    theta_tete = r.deplacements[-1, 2]
    assert u_tete == pytest.approx(P * _L_TOTAL**3 / (3 * _EI))
    assert theta_tete == pytest.approx(P * _L_TOTAL**2 / (2 * _EI))

    # M constant en flexion pure sans charge répartie : linéaire entre M(0)=-P·L et M(L)=0
    assert r.moment_flechissant[0, 0] == pytest.approx(-P * _L_TOTAL)
    assert r.moment_flechissant[-1, 1] == pytest.approx(0.0, abs=1e-8)
    # V constant = P sur toute la hauteur
    assert np.allclose(r.effort_tranchant, P)


def test_console_moment_en_tete():
    m = _maillage(1)
    ea = [_EA]
    ei = [_EI]
    appuis = ConditionsAppui(pied=TypeAppuiPied.ENCASTREMENT, tete=TypeAppuiTete.LIBRE)
    M0 = 12.0
    F = np.zeros(m.nb_dof)
    F[3 * (m.nb_noeuds - 1) + 2] = M0  # θ au dernier nœud

    r = resoudre(m, ea, ei, appuis, _SOL, _GEOMETRIE, F)

    theta_tete = r.deplacements[-1, 2]
    assert theta_tete == pytest.approx(M0 * _L_TOTAL / _EI)
    # Flexion pure : M constant = -M0, V nul
    assert r.moment_flechissant[0, 0] == pytest.approx(-M0)
    assert r.moment_flechissant[0, 1] == pytest.approx(-M0)
    assert np.allclose(r.effort_tranchant, 0.0, atol=1e-8)


def test_console_charge_axiale_en_tete():
    m = _maillage(2)
    ea = [_EA] * m.nb_elements
    ei = [_EI] * m.nb_elements
    appuis = ConditionsAppui(pied=TypeAppuiPied.ENCASTREMENT, tete=TypeAppuiTete.LIBRE)
    N_ext = 200e3
    F = np.zeros(m.nb_dof)
    F[3 * (m.nb_noeuds - 1)] = N_ext  # w au dernier nœud

    r = resoudre(m, ea, ei, appuis, _SOL, _GEOMETRIE, F)

    w_tete = r.deplacements[-1, 0]
    assert w_tete == pytest.approx(N_ext * _L_TOTAL / _EA)
    assert np.allclose(r.effort_normal, N_ext)


def test_encastrement_elastique_moment_en_tete():
    m = _maillage(1)
    ea = [_EA]
    ei = [_EI]
    k_theta = 8000.0
    appuis = ConditionsAppui(pied=TypeAppuiPied.RESSORT, tete=TypeAppuiTete.LIBRE, k_theta=k_theta)
    M0 = 12.0
    F = np.zeros(m.nb_dof)
    F[3 * (m.nb_noeuds - 1) + 2] = M0

    r = resoudre(m, ea, ei, appuis, _SOL, _GEOMETRIE, F)

    theta_pied = r.deplacements[0, 2]
    theta_tete = r.deplacements[-1, 2]
    assert theta_pied == pytest.approx(M0 / k_theta)
    assert theta_tete == pytest.approx(theta_pied + M0 * _L_TOTAL / _EI)
    assert r.moment_flechissant[0, 0] == pytest.approx(-M0)


def test_aucune_charge_donne_une_solution_nulle():
    m = _maillage(2)
    ea = [_EA] * m.nb_elements
    ei = [_EI] * m.nb_elements
    appuis = ConditionsAppui(pied=TypeAppuiPied.ENCASTREMENT, tete=TypeAppuiTete.LIBRE)
    F = np.zeros(m.nb_dof)

    r = resoudre(m, ea, ei, appuis, _SOL, _GEOMETRIE, F)

    assert np.allclose(r.deplacements, 0.0)
    assert np.allclose(r.effort_normal, 0.0)
    assert np.allclose(r.effort_tranchant, 0.0)
    assert np.allclose(r.moment_flechissant, 0.0)


def test_appui_dalle_bloque_bien_le_deplacement_horizontal_en_tete():
    m = _maillage(2)
    ea = [_EA] * m.nb_elements
    ei = [_EI] * m.nb_elements
    appuis = ConditionsAppui(pied=TypeAppuiPied.ENCASTREMENT, tete=TypeAppuiTete.APPUI_DALLE)
    P = 15.0
    F = np.zeros(m.nb_dof)
    F[3 * 1 + 1] = P  # charge horizontale au nœud intermédiaire

    r = resoudre(m, ea, ei, appuis, _SOL, _GEOMETRIE, F)
    assert r.deplacements[-1, 1] == pytest.approx(0.0, abs=1e-10)

    # équilibre horizontal global : réaction au pied + réaction en tête + charge appliquée = 0
    K = assembler(m, ea, ei)
    d = r.deplacements.reshape(-1)
    residu = K @ d - F
    dof_u_pied, dof_u_tete = 1, 3 * (m.nb_noeuds - 1) + 1
    assert residu[dof_u_pied] + residu[dof_u_tete] + P == pytest.approx(0.0, abs=1e-6)


def test_forces_nodales_de_mauvaise_taille_leve_une_erreur():
    m = _maillage(2)
    ea = [_EA] * m.nb_elements
    ei = [_EI] * m.nb_elements
    appuis = ConditionsAppui()
    with pytest.raises(ValueError):
        resoudre(m, ea, ei, appuis, _SOL, _GEOMETRIE, np.zeros(3))
