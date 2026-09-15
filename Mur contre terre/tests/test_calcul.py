import numpy as np
import pytest

from mur_contre_terre.calcul import calculer, verifier_section
from mur_contre_terre.donnees.appuis import ConditionsAppui, TypeAppuiPied, TypeAppuiTete
from mur_contre_terre.donnees.charges import CasDeCharge, CategorieAction, TypeCharge
from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.donnees.materiaux import Acier, Beton, Materiaux
from mur_contre_terre.donnees.projet import Projet
from mur_contre_terre.donnees.sol import Sol, TypePoussee
from mur_contre_terre.mecanique.maillage import Maillage
from mur_contre_terre.mecanique.solveur_lineaire import ResultatMecanique
from mur_contre_terre.unites import deg, kN, kN_m3


def _projet() -> Projet:
    return Projet(
        nom="Test",
        geometrie=Geometrie(hauteur=3.0, ep_base=0.30, ep_couronnement=0.20, debord_semelle=0.8, ep_semelle=0.4),
        sol=Sol(gamma=kN_m3(18), phi=deg(30), delta=deg(20), type_poussee=TypePoussee.ACTIF),
        appuis=ConditionsAppui(pied=TypeAppuiPied.ENCASTREMENT, tete=TypeAppuiTete.LIBRE),
        materiaux=Materiaux(
            beton=Beton.depuis_classe("C30/37"), acier=Acier.b500b(), enrobage_terre=0.05, enrobage_interieur=0.04
        ),
        charges=(
            CasDeCharge(nom="Poids propre", type=TypeCharge.POIDS_PROPRE, categorie=CategorieAction.G, valeur=0.0),
            CasDeCharge(nom="Poussee", type=TypeCharge.POUSSEE_TERRES, categorie=CategorieAction.G, valeur=0.0),
            CasDeCharge(
                nom="Charge tete", type=TypeCharge.CHARGE_TETE, categorie=CategorieAction.Q, valeur=kN(30),
                psi0=0.7, psi1=0.5, psi2=0.3,
            ),
        ),
        finesse_maillage=0.5,
    )


def test_calculer_produit_une_verification_par_element():
    r = calculer(_projet())
    assert len(r.verifications) == r.maillage.nb_elements
    assert len(r.resultats_elu) == len(r.combinaisons_elu)
    assert len(r.resultats_els) == len(r.combinaisons_els)


def test_calculer_verifications_sont_physiquement_plausibles():
    r = calculer(_projet())
    for v in r.verifications:
        assert v.armature_terre > 0.0
        assert v.armature_interieur > 0.0
        assert v.effort_tranchant_ed >= 0.0
        assert v.effort_tranchant_rd > 0.0
        assert v.verdict_tranchant == (v.effort_tranchant_ed <= v.effort_tranchant_rd)


def test_calculer_effort_tranchant_decroit_vers_la_tete():
    # la poussée des terres croît avec la profondeur : l'effort tranchant est maximal au pied
    r = calculer(_projet())
    v_ed = [v.effort_tranchant_ed for v in r.verifications]
    assert v_ed[0] > v_ed[-1]
    assert v_ed == sorted(v_ed, reverse=True)


def _maillage_deux_elements() -> Maillage:
    return Maillage((0.0, 1.0, 2.0))


def _geometrie() -> Geometrie:
    return Geometrie(hauteur=2.0, ep_base=0.30, ep_couronnement=0.30, debord_semelle=0.6, ep_semelle=0.3)


def _materiaux() -> Materiaux:
    return Materiaux(
        beton=Beton.depuis_classe("C30/37"), acier=Acier.b500b(), enrobage_terre=0.05, enrobage_interieur=0.04
    )


def _resultat_synthetique(maillage: Maillage, n: float, m: float, v: float = 1.0e3) -> ResultatMecanique:
    n_el = maillage.nb_elements
    return ResultatMecanique(
        maillage=maillage,
        deplacements=np.zeros((maillage.nb_noeuds, 3)),
        effort_normal=np.full((n_el, 2), n),
        effort_tranchant=np.full((n_el, 2), v),
        moment_flechissant=np.full((n_el, 2), m),
    )


def test_verifier_section_moment_negatif_dimensionne_la_face_terre():
    # Convention vérifiée physiquement (voir calcul.py) : M < 0 tend la face terre.
    m = _maillage_deux_elements()
    resultats = (_resultat_synthetique(m, n=0.0, m=-50e3),)
    v = verifier_section(0, _geometrie(), _materiaux(), m, resultats)
    # La face terre reçoit l'armature calculée par flexion composée (> minimum) ; la face
    # intérieure ne reçoit que l'armature minimale (M ne la sollicite jamais en tension ici).
    assert v.armature_terre > v.armature_interieur


def test_verifier_section_moment_positif_dimensionne_la_face_interieure():
    m = _maillage_deux_elements()
    resultats = (_resultat_synthetique(m, n=0.0, m=50e3),)
    v = verifier_section(0, _geometrie(), _materiaux(), m, resultats)
    assert v.armature_interieur > v.armature_terre


def test_verifier_section_enveloppe_sur_plusieurs_combinaisons():
    m = _maillage_deux_elements()
    resultats = (
        _resultat_synthetique(m, n=0.0, m=-50e3),
        _resultat_synthetique(m, n=0.0, m=30e3),
    )
    v = verifier_section(0, _geometrie(), _materiaux(), m, resultats)
    # Les deux faces sont sollicitées par des combinaisons différentes : les deux dépassent le minimum.
    v_terre_seule = verifier_section(0, _geometrie(), _materiaux(), m, resultats[:1])
    v_interieur_seule = verifier_section(0, _geometrie(), _materiaux(), m, resultats[1:])
    assert v.armature_terre == pytest.approx(v_terre_seule.armature_terre)
    assert v.armature_interieur == pytest.approx(v_interieur_seule.armature_interieur)


def test_verifier_section_effort_tranchant_est_le_maximum_absolu():
    m = _maillage_deux_elements()
    resultats = (
        _resultat_synthetique(m, n=0.0, m=1e3, v=10e3),
        _resultat_synthetique(m, n=0.0, m=1e3, v=-40e3),
    )
    v = verifier_section(0, _geometrie(), _materiaux(), m, resultats)
    assert v.effort_tranchant_ed == pytest.approx(40e3)
