"""Conversion des charges du cahier des charges en vecteurs de charges nodales.

Convention de signe (choix de modélisation, à respecter partout) :
``+u`` pointe du côté terre vers le côté intérieur — c'est le sens dans
lequel la poussée des terres pousse le mur, donc toutes les pressions
latérales (poussée, hydrostatique, compactage, surcharges) s'appliquent en
``+u``. ``+w`` pointe vers le haut (même sens que ``Geometrie``/
``Maillage``, ``z`` croissant du pied vers la tête) : le poids propre et
la composante verticale de frottement de la poussée (§7 du plan de
conception) s'appliquent donc en ``-w``.

Les charges réparties sont linéaires par élément (valeurs aux nœuds) et
converties en efforts nodaux équivalents cohérents avec les fonctions de
forme utilisées pour la rigidité (``rigidite.py``) — formules classiques
de chargement réparti trapézoïdal, vérifiées par équilibre et par
convergence de maillage (voir tests).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from mur_contre_terre.donnees.charges import CasDeCharge, TypeCharge
from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.donnees.materiaux import Materiaux
from mur_contre_terre.donnees.sol import Sol
from mur_contre_terre.geotechnique.compactage import pression_compactage
from mur_contre_terre.geotechnique.hydrostatique import pression_hydrostatique
from mur_contre_terre.geotechnique.poussee import profil_poussee
from mur_contre_terre.geotechnique.surcharges import pression_charge_lineaire, pression_charge_surfacique
from mur_contre_terre.mecanique.maillage import Maillage


def charge_repartie_axiale_element(q1: float, q2: float, longueur: float) -> tuple[float, float]:
    """Forces nodales équivalentes (N1, N2) pour une charge axiale linéaire de q1 à q2."""
    L = longueur
    f1 = L * (2.0 * q1 + q2) / 6.0
    f2 = L * (q1 + 2.0 * q2) / 6.0
    return f1, f2


def charge_repartie_transversale_element(q1: float, q2: float, longueur: float) -> tuple[float, float, float, float]:
    """Forces/moments nodaux équivalents (F1, M1, F2, M2) pour une charge transversale linéaire."""
    L = longueur
    f1 = L / 20.0 * (7.0 * q1 + 3.0 * q2)
    m1 = L**2 / 60.0 * (3.0 * q1 + 2.0 * q2)
    f2 = L / 20.0 * (3.0 * q1 + 7.0 * q2)
    m2 = -(L**2) / 60.0 * (2.0 * q1 + 3.0 * q2)
    return f1, m1, f2, m2


def assembler_charge_axiale(maillage: Maillage, valeurs_par_noeud: Sequence[float]) -> np.ndarray:
    """Vecteur global (DOF w) à partir d'une charge linéique [N/m] connue à chaque nœud."""
    if len(valeurs_par_noeud) != maillage.nb_noeuds:
        raise ValueError(f"valeurs_par_noeud doit avoir {maillage.nb_noeuds} valeurs")
    F = np.zeros(maillage.nb_dof)
    for i in range(maillage.nb_elements):
        f1, f2 = charge_repartie_axiale_element(
            valeurs_par_noeud[i], valeurs_par_noeud[i + 1], maillage.longueur_element(i)
        )
        F[3 * i] += f1
        F[3 * (i + 1)] += f2
    return F


def assembler_charge_transversale(maillage: Maillage, valeurs_par_noeud: Sequence[float]) -> np.ndarray:
    """Vecteur global (DOF u, θ) à partir d'une charge linéique [N/m] connue à chaque nœud."""
    if len(valeurs_par_noeud) != maillage.nb_noeuds:
        raise ValueError(f"valeurs_par_noeud doit avoir {maillage.nb_noeuds} valeurs")
    F = np.zeros(maillage.nb_dof)
    for i in range(maillage.nb_elements):
        f1, m1, f2, m2 = charge_repartie_transversale_element(
            valeurs_par_noeud[i], valeurs_par_noeud[i + 1], maillage.longueur_element(i)
        )
        F[3 * i + 1] += f1
        F[3 * i + 2] += m1
        F[3 * (i + 1) + 1] += f2
        F[3 * (i + 1) + 2] += m2
    return F


def poids_propre(geometrie: Geometrie, materiaux: Materiaux, maillage: Maillage) -> np.ndarray:
    """Poids propre du mur — SIA 261 §5.3, calculé automatiquement."""
    valeurs = [-materiaux.beton.poids_volumique * geometrie.epaisseur(z) for z in maillage.positions]
    return assembler_charge_axiale(maillage, valeurs)


def charge_tete(maillage: Maillage, valeur: float, excentricite: float = 0.0) -> np.ndarray:
    """Charge verticale ponctuelle en tête (bâtiment), avec excentricité éventuelle."""
    F = np.zeros(maillage.nb_dof)
    noeud_tete = maillage.nb_noeuds - 1
    F[3 * noeud_tete] += -valeur
    F[3 * noeud_tete + 2] += -valeur * excentricite
    return F


def poussee_des_terres(sol: Sol, geometrie: Geometrie, maillage: Maillage, g0: float = 0.0) -> np.ndarray:
    """Poussée des terres — composantes horizontale (e_ah) et verticale (e_av)."""
    e_ah_par_noeud: list[float] = []
    e_av_par_noeud: list[float] = []
    for z in maillage.positions:
        profondeur = geometrie.hauteur - z
        e_ah, e_av = profil_poussee(sol, geometrie.hauteur, profondeur, g0=g0)
        e_ah_par_noeud.append(e_ah)
        e_av_par_noeud.append(-e_av)
    return assembler_charge_transversale(maillage, e_ah_par_noeud) + assembler_charge_axiale(maillage, e_av_par_noeud)


def hydrostatique(sol: Sol, geometrie: Geometrie, maillage: Maillage) -> np.ndarray:
    """Pression hydrostatique côté terre."""
    valeurs = [pression_hydrostatique(sol, geometrie.hauteur, geometrie.hauteur - z) for z in maillage.positions]
    return assembler_charge_transversale(maillage, valeurs)


def compactage(geometrie: Geometrie, maillage: Maillage, intensite: float, profondeur_application: float) -> np.ndarray:
    """Pression de compactage."""
    valeurs = [pression_compactage(intensite, profondeur_application, geometrie.hauteur - z) for z in maillage.positions]
    return assembler_charge_transversale(maillage, valeurs)


def charge_lineaire_terreplein(geometrie: Geometrie, maillage: Maillage, intensite: float, distance: float) -> np.ndarray:
    """Charge linéaire sur le terre-plein, parallèle au mur."""
    valeurs = [pression_charge_lineaire(intensite, distance, geometrie.hauteur - z) for z in maillage.positions]
    return assembler_charge_transversale(maillage, valeurs)


def charge_surfacique_terreplein(
    geometrie: Geometrie, maillage: Maillage, intensite: float, distance: float, etendue: float
) -> np.ndarray:
    """Charge surfacique sur le terre-plein (bande [distance, distance+étendue])."""
    valeurs = [
        pression_charge_surfacique(intensite, distance, etendue, geometrie.hauteur - z) for z in maillage.positions
    ]
    return assembler_charge_transversale(maillage, valeurs)


def vecteur_charge(
    charge: CasDeCharge, sol: Sol, geometrie: Geometrie, materiaux: Materiaux, maillage: Maillage
) -> np.ndarray:
    """Vecteur de charges nodales pour un ``CasDeCharge``, selon son ``TypeCharge``.

    ``SURCHARGE_TETE`` module ``g0`` dans la formule de poussée (§4.3.2.3) :
    son vecteur est la *différence* entre la poussée avec et sans cette
    surcharge, pour que ``POUSSEE_TERRES`` et ``SURCHARGE_TETE`` restent
    deux actions distinctes, chacune combinable avec son propre facteur
    partiel (nécessaire dès que leur catégorie G/Q diffère).
    """
    if charge.type is TypeCharge.POIDS_PROPRE:
        return poids_propre(geometrie, materiaux, maillage)
    if charge.type is TypeCharge.CHARGE_TETE:
        return charge_tete(maillage, charge.valeur, charge.parametres.get("excentricite", 0.0))
    if charge.type is TypeCharge.POUSSEE_TERRES:
        return poussee_des_terres(sol, geometrie, maillage, g0=0.0)
    if charge.type is TypeCharge.SURCHARGE_TETE:
        return poussee_des_terres(sol, geometrie, maillage, g0=charge.valeur) - poussee_des_terres(
            sol, geometrie, maillage, g0=0.0
        )
    if charge.type is TypeCharge.PRESSION_HYDROSTATIQUE:
        return hydrostatique(sol, geometrie, maillage)
    if charge.type is TypeCharge.PRESSION_COMPACTAGE:
        return compactage(geometrie, maillage, charge.valeur, charge.parametres["profondeur_application"])
    if charge.type is TypeCharge.CHARGE_LINEAIRE_TERREPLEIN:
        return charge_lineaire_terreplein(geometrie, maillage, charge.valeur, charge.parametres["distance"])
    if charge.type is TypeCharge.CHARGE_SURFACIQUE_TERREPLEIN:
        return charge_surfacique_terreplein(
            geometrie, maillage, charge.valeur, charge.parametres.get("distance", 0.0), charge.parametres["etendue"]
        )
    raise ValueError(f"Type de charge non géré : {charge.type}")
