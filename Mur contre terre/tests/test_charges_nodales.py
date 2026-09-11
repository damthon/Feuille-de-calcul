import numpy as np
import pytest

from mur_contre_terre.donnees.appuis import ConditionsAppui, TypeAppuiPied, TypeAppuiTete
from mur_contre_terre.donnees.charges import CasDeCharge, CategorieAction, TypeCharge
from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.donnees.materiaux import Acier, Beton, Materiaux
from mur_contre_terre.donnees.sol import Sol, TypePoussee
from mur_contre_terre.mecanique.charges_nodales import (
    assembler_charge_axiale,
    assembler_charge_transversale,
    charge_repartie_axiale_element,
    charge_repartie_transversale_element,
    charge_tete,
    poids_propre,
    poussee_des_terres,
    vecteur_charge,
)
from mur_contre_terre.mecanique.maillage import Maillage, generer_maillage
from mur_contre_terre.mecanique.rigidite import rigidites_par_element
from mur_contre_terre.mecanique.solveur_lineaire import resoudre
from mur_contre_terre.unites import deg, kN, kN_m3

_GEOMETRIE = Geometrie(hauteur=3.0, ep_base=0.30, ep_couronnement=0.30, debord_semelle=0.8, ep_semelle=0.4)
_MATERIAUX = Materiaux(beton=Beton.depuis_classe("C30/37"), acier=Acier.b500b(), enrobage_terre=0.05, enrobage_interieur=0.04)
_SOL = Sol(gamma=kN_m3(18), phi=deg(30), delta=0.0, type_poussee=TypePoussee.ACTIF)


def test_charge_repartie_axiale_uniforme_egale_qL_sur_2():
    f1, f2 = charge_repartie_axiale_element(q1=1000.0, q2=1000.0, longueur=2.0)
    assert f1 == pytest.approx(1000.0)
    assert f2 == pytest.approx(1000.0)


def test_charge_repartie_axiale_equilibre_force():
    q1, q2, L = 300.0, 900.0, 2.5
    f1, f2 = charge_repartie_axiale_element(q1, q2, L)
    assert f1 + f2 == pytest.approx(L * (q1 + q2) / 2.0)


def test_charge_repartie_transversale_uniforme_donne_les_moments_d_encastrement_classiques():
    q, L = 1000.0, 2.0
    f1, m1, f2, m2 = charge_repartie_transversale_element(q, q, L)
    assert f1 == pytest.approx(q * L / 2.0)
    assert f2 == pytest.approx(q * L / 2.0)
    assert m1 == pytest.approx(q * L**2 / 12.0)
    assert m2 == pytest.approx(-q * L**2 / 12.0)


def test_charge_repartie_transversale_equilibre_force_et_moment():
    q1, q2, L = 200.0, 800.0, 3.0
    f1, m1, f2, m2 = charge_repartie_transversale_element(q1, q2, L)
    assert f1 + f2 == pytest.approx(L * (q1 + q2) / 2.0)
    moment_distribue_origine = L**2 * (q1 + 2 * q2) / 6.0
    assert m1 + m2 + f2 * L == pytest.approx(moment_distribue_origine)


def test_assembler_charge_axiale_continuite_aux_noeuds_interieurs():
    m = Maillage((0.0, 1.0, 2.0))
    F = assembler_charge_axiale(m, valeurs_par_noeud=[100.0, 100.0, 100.0])
    # nœud du milieu reçoit la contribution des deux éléments adjacents
    assert F[3] == pytest.approx(2 * 100.0 * 1.0 / 2.0)


def test_assembler_charge_mauvaise_taille_leve_une_erreur():
    m = Maillage((0.0, 1.0, 2.0))
    with pytest.raises(ValueError):
        assembler_charge_axiale(m, [1.0, 2.0])
    with pytest.raises(ValueError):
        assembler_charge_transversale(m, [1.0, 2.0])


def test_poids_propre_somme_egale_au_poids_total():
    m = generer_maillage(_GEOMETRIE, finesse=0.5)
    F = poids_propre(_GEOMETRIE, _MATERIAUX, m)
    poids_total = _MATERIAUX.beton.poids_volumique * _GEOMETRIE.ep_base * _GEOMETRIE.hauteur
    dofs_w = list(range(0, m.nb_dof, 3))
    assert F[dofs_w].sum() == pytest.approx(-poids_total)
    # aucune composante transversale ni de moment
    autres = [i for i in range(m.nb_dof) if i not in dofs_w]
    assert np.allclose(F[autres], 0.0)


def test_poids_propre_ne_cree_aucun_deplacement_horizontal():
    m = generer_maillage(_GEOMETRIE, finesse=0.5)
    ea, ei = rigidites_par_element(_GEOMETRIE, _MATERIAUX, m)
    appuis = ConditionsAppui(pied=TypeAppuiPied.ENCASTREMENT, tete=TypeAppuiTete.LIBRE)
    F = poids_propre(_GEOMETRIE, _MATERIAUX, m)
    r = resoudre(m, ea, ei, appuis, _SOL, _GEOMETRIE, F)
    assert np.allclose(r.deplacements[:, 1], 0.0)  # u
    assert np.allclose(r.deplacements[:, 2], 0.0)  # theta
    assert np.all(r.deplacements[:, 0] <= 0.0)  # w : tassement vers le bas


def test_charge_tete_place_la_force_et_le_moment_au_dernier_noeud():
    m = Maillage((0.0, 1.0, 2.0))
    F = charge_tete(m, valeur=kN(80), excentricite=0.05)
    assert F[6] == pytest.approx(-kN(80))
    assert F[8] == pytest.approx(-kN(80) * 0.05)
    assert F[0] == 0.0 and F[3] == 0.0


def test_poussee_des_terres_pousse_le_mur_vers_l_interieur():
    m = generer_maillage(_GEOMETRIE, finesse=0.5)
    ea, ei = rigidites_par_element(_GEOMETRIE, _MATERIAUX, m)
    appuis = ConditionsAppui(pied=TypeAppuiPied.ENCASTREMENT, tete=TypeAppuiTete.LIBRE)
    F = poussee_des_terres(_SOL, _GEOMETRIE, m)
    r = resoudre(m, ea, ei, appuis, _SOL, _GEOMETRIE, F)
    assert r.deplacements[-1, 1] > 0.0  # u en tête, +u = vers l'intérieur


def test_poussee_des_terres_delta_nul_ne_cree_pas_de_composante_axiale():
    m = Maillage((0.0, 1.5, 3.0))
    F = poussee_des_terres(_SOL, _GEOMETRIE, m)  # _SOL a delta=0.0
    dofs_w = list(range(0, m.nb_dof, 3))
    assert np.allclose(F[dofs_w], 0.0)


def test_vecteur_charge_dispatch_poids_propre():
    charge = CasDeCharge(nom="Poids propre", type=TypeCharge.POIDS_PROPRE, categorie=CategorieAction.G, valeur=0.0)
    m = generer_maillage(_GEOMETRIE, finesse=0.5)
    attendu = poids_propre(_GEOMETRIE, _MATERIAUX, m)
    obtenu = vecteur_charge(charge, _SOL, _GEOMETRIE, _MATERIAUX, m)
    assert np.allclose(obtenu, attendu)


def test_vecteur_charge_dispatch_charge_tete_avec_excentricite():
    charge = CasDeCharge(
        nom="Charge bâtiment", type=TypeCharge.CHARGE_TETE, categorie=CategorieAction.G, valeur=kN(80),
        parametres={"excentricite": 0.05},
    )
    m = Maillage((0.0, 1.0, 2.0))
    obtenu = vecteur_charge(charge, _SOL, _GEOMETRIE, _MATERIAUX, m)
    assert obtenu[6] == pytest.approx(-kN(80))
    assert obtenu[8] == pytest.approx(-kN(80) * 0.05)


def test_vecteur_charge_surcharge_tete_est_incrementale():
    charge_poussee = CasDeCharge(nom="Poussée", type=TypeCharge.POUSSEE_TERRES, categorie=CategorieAction.G, valeur=0.0)
    charge_surcharge = CasDeCharge(
        nom="Surcharge", type=TypeCharge.SURCHARGE_TETE, categorie=CategorieAction.G, valeur=5e3,
    )
    m = generer_maillage(_GEOMETRIE, finesse=0.5)
    v_poussee = vecteur_charge(charge_poussee, _SOL, _GEOMETRIE, _MATERIAUX, m)
    v_surcharge = vecteur_charge(charge_surcharge, _SOL, _GEOMETRIE, _MATERIAUX, m)
    v_poussee_avec_g0 = poussee_des_terres(_SOL, _GEOMETRIE, m, g0=5e3)
    assert np.allclose(v_poussee + v_surcharge, v_poussee_avec_g0)


def test_vecteur_charge_parametre_manquant_leve_une_erreur():
    charge = CasDeCharge(
        nom="Compactage", type=TypeCharge.PRESSION_COMPACTAGE, categorie=CategorieAction.Q, valeur=8e3,
    )
    m = Maillage((0.0, 1.0, 2.0))
    with pytest.raises(KeyError):
        vecteur_charge(charge, _SOL, _GEOMETRIE, _MATERIAUX, m)  # profondeur_application manquant
