import numpy as np
import pytest

from mur_contre_terre.donnees.appuis import ConditionsAppui, TypeAppuiPied, TypeAppuiTete
from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.donnees.materiaux import Acier, Beton, Materiaux
from mur_contre_terre.donnees.sol import Sol
from mur_contre_terre.mecanique.maillage import Maillage
from mur_contre_terre.mecanique.rigidite import rigidites_par_element
from mur_contre_terre.mecanique.solveur_lineaire import resoudre
from mur_contre_terre.nonlineaire.solveur_incremental import resoudre_incremental
from mur_contre_terre.unites import deg, kN_m3

_GEOMETRIE = Geometrie(hauteur=2.0, ep_base=0.25, ep_couronnement=0.25, debord_semelle=0.6, ep_semelle=0.3)
_SOL = Sol(gamma=kN_m3(18), phi=deg(30))
_MATERIAUX = Materiaux(
    beton=Beton.depuis_classe("C30/37"), acier=Acier.b500b(), enrobage_terre=0.04, enrobage_interieur=0.04
)
_APPUIS = ConditionsAppui(pied=TypeAppuiPied.ENCASTREMENT, tete=TypeAppuiTete.LIBRE)


def _maillage() -> Maillage:
    return Maillage((0.0, 1.0, 2.0))  # 2 éléments, volontairement grossier pour la vitesse des tests


def _forces(maillage: Maillage, valeur: float) -> np.ndarray:
    F = np.zeros(maillage.nb_dof)
    F[3 * (maillage.nb_noeuds - 1) + 1] = valeur
    return F


def test_forces_nodales_de_mauvaise_taille_leve_une_erreur():
    m = _maillage()
    with pytest.raises(ValueError):
        resoudre_incremental(m, _GEOMETRIE, _MATERIAUX, _APPUIS, _SOL, np.zeros(3), 6e-4, 6e-4)


def test_armature_de_mauvaise_taille_leve_une_erreur():
    m = _maillage()
    F = _forces(m, 1.0e3)
    with pytest.raises(ValueError):
        resoudre_incremental(m, _GEOMETRIE, _MATERIAUX, _APPUIS, _SOL, F, (6e-4, 6e-4, 6e-4), 6e-4)


@pytest.mark.parametrize("kwargs", [{"nb_paliers": 0}, {"tolerance": 0.0}, {"tolerance": 1.5}, {"max_iterations": 0}])
def test_parametres_invalides_levent_une_erreur(kwargs):
    m = _maillage()
    F = _forces(m, 1.0e3)
    with pytest.raises(ValueError):
        resoudre_incremental(m, _GEOMETRIE, _MATERIAUX, _APPUIS, _SOL, F, 6e-4, 6e-4, **kwargs)


def test_petite_charge_convergence_totale_et_coherente_avec_le_solveur_lineaire():
    m = _maillage()
    charge_totale = 5.0e3  # faible : la section reste quasi non fissurée sur tout le trajet
    F = _forces(m, charge_totale)

    resultat = resoudre_incremental(
        m, _GEOMETRIE, _MATERIAUX, _APPUIS, _SOL, F, armature_terre=6e-4, armature_interieur=6e-4, nb_paliers=4
    )

    assert resultat.convergence_totale
    assert resultat.fraction_charge_maximale == pytest.approx(1.0)
    assert len(resultat.paliers) == 4

    # Déplacements croissants avec la charge
    deplacements_tete = [p.resultat.deplacements[-1, 1] for p in resultat.paliers]
    assert deplacements_tete == sorted(deplacements_tete)
    assert deplacements_tete[-1] > 0.0

    # À faible charge (section quasi non fissurée), le résultat doit être proche de l'élastique linéaire
    ea, ei_elastique = rigidites_par_element(_GEOMETRIE, _MATERIAUX, m)
    resultat_elastique = resoudre(m, ea, ei_elastique, _APPUIS, _SOL, _GEOMETRIE, F)
    assert deplacements_tete[-1] == pytest.approx(resultat_elastique.deplacements[-1, 1], rel=0.05)


def test_ei_decroit_avec_la_fissuration():
    m = _maillage()
    F = _forces(m, 60.0e3)  # charge assez forte pour fissurer nettement

    resultat = resoudre_incremental(
        m, _GEOMETRIE, _MATERIAUX, _APPUIS, _SOL, F, armature_terre=8e-4, armature_interieur=8e-4, nb_paliers=4
    )

    ei_premier = resultat.paliers[0].ei[0]
    ei_dernier = resultat.paliers[-1].ei[0]
    assert ei_dernier < ei_premier


def test_armature_scalaire_equivaut_a_un_tableau_constant():
    m = _maillage()
    F = _forces(m, 5.0e3)

    r_scalaire = resoudre_incremental(m, _GEOMETRIE, _MATERIAUX, _APPUIS, _SOL, F, 6e-4, 6e-4, nb_paliers=2)
    r_tableau = resoudre_incremental(
        m, _GEOMETRIE, _MATERIAUX, _APPUIS, _SOL, F, (6e-4, 6e-4), (6e-4, 6e-4), nb_paliers=2
    )

    u_scalaire = r_scalaire.paliers[-1].resultat.deplacements[-1, 1]
    u_tableau = r_tableau.paliers[-1].resultat.deplacements[-1, 1]
    assert u_scalaire == pytest.approx(u_tableau)


def test_armature_insuffisante_arrete_avant_pleine_charge():
    m = _maillage()
    F = _forces(m, 200.0e3)  # charge très forte pour une armature minimale

    resultat = resoudre_incremental(
        m, _GEOMETRIE, _MATERIAUX, _APPUIS, _SOL, F, armature_terre=1e-5, armature_interieur=1e-5, nb_paliers=10
    )

    assert not resultat.convergence_totale
    assert resultat.fraction_charge_maximale < 1.0
    assert len(resultat.paliers) < 10
