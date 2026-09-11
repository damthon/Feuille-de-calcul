"""Rigidité élémentaire et assemblage — poutre d'Euler-Bernoulli verticale.

Le mur étant un élément droit et vertical, l'axe local de chaque élément
coïncide avec l'axe global : aucune transformation de repère n'est
nécessaire. Degrés de liberté locaux (et globaux) par nœud :
``[w, u, θ]`` — w axial (vertical), u transversal (horizontal), θ rotation.

Section évaluée au milieu de chaque élément (``Geometrie.epaisseur``) :
approximation usuelle d'une poutre à inertie variable par une suite
d'éléments prismatiques, dont l'erreur diminue avec la finesse du
maillage choisie par l'utilisateur.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.donnees.materiaux import Materiaux
from mur_contre_terre.mecanique.maillage import Maillage

# Ordre local : [w1, u1, θ1, w2, u2, θ2]
_DOF_AXIAL = (0, 3)
_DOF_FLEXION = (1, 2, 4, 5)


def k_element(ea: float, ei: float, longueur: float) -> np.ndarray:
    """Matrice de rigidité 6×6 d'un élément prismatique, repère local = global."""
    if longueur <= 0:
        raise ValueError(f"longueur doit être strictement positive (reçu {longueur})")
    L = longueur
    k = np.zeros((6, 6))

    ka = ea / L * np.array([[1.0, -1.0], [-1.0, 1.0]])
    for i, gi in enumerate(_DOF_AXIAL):
        for j, gj in enumerate(_DOF_AXIAL):
            k[gi, gj] = ka[i, j]

    kf = ei / L**3 * np.array([
        [12.0, 6.0 * L, -12.0, 6.0 * L],
        [6.0 * L, 4.0 * L**2, -6.0 * L, 2.0 * L**2],
        [-12.0, -6.0 * L, 12.0, -6.0 * L],
        [6.0 * L, 2.0 * L**2, -6.0 * L, 4.0 * L**2],
    ])
    for i, gi in enumerate(_DOF_FLEXION):
        for j, gj in enumerate(_DOF_FLEXION):
            k[gi, gj] = kf[i, j]

    return k


def rigidites_par_element(
    geometrie: Geometrie, materiaux: Materiaux, maillage: Maillage
) -> tuple[list[float], list[float]]:
    """(EA, EI) par élément — section brute non fissurée (Ecm), tranche de 1,00 m."""
    ea: list[float] = []
    ei: list[float] = []
    for i in range(maillage.nb_elements):
        epaisseur = geometrie.epaisseur(maillage.milieu_element(i))
        aire = epaisseur * 1.0
        inertie = 1.0 * epaisseur**3 / 12.0
        ea.append(materiaux.beton.Ecm * aire)
        ei.append(materiaux.beton.Ecm * inertie)
    return ea, ei


def assembler(maillage: Maillage, ea: Sequence[float], ei: Sequence[float]) -> np.ndarray:
    """Matrice de rigidité globale (assemblage direct, DOF d'éléments contigus)."""
    if len(ea) != maillage.nb_elements or len(ei) != maillage.nb_elements:
        raise ValueError("ea et ei doivent avoir une valeur par élément du maillage")
    K = np.zeros((maillage.nb_dof, maillage.nb_dof))
    for i in range(maillage.nb_elements):
        ke = k_element(ea[i], ei[i], maillage.longueur_element(i))
        dofs = list(maillage.dofs_element(i))
        K[np.ix_(dofs, dofs)] += ke
    return K
