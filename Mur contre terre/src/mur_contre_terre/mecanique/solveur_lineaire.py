"""Résolution linéaire élastique K·u = F et récupération des efforts internes.

Convention de signe des efforts internes par élément (calibrée et
vérifiée contre les solutions fermées d'une console — voir
``tests/test_solveur_lineaire.py``) : pour un élément de nœuds locaux 1
(début, ``z`` le plus petit) et 2 (fin), avec ``q = k_element @ d_element``
dans l'ordre ``[N1, V1, M1, N2, V2, M2]`` :

    N(début) = −N1   N(fin) = +N2
    V(début) = −V1   V(fin) = +V2
    M(début) = +M1   M(fin) = −M2

Sans charge répartie à l'intérieur d'un élément (lot 3 : uniquement des
charges nodales), N et V y sont constants et M y varie linéairement.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from mur_contre_terre.donnees.appuis import ConditionsAppui
from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.donnees.sol import Sol
from mur_contre_terre.mecanique.appuis import dofs_bloques, rigidite_ressort_pied
from mur_contre_terre.mecanique.maillage import Maillage
from mur_contre_terre.mecanique.rigidite import assembler, k_element


@dataclass(frozen=True)
class ResultatMecanique:
    maillage: Maillage
    deplacements: np.ndarray  # (nb_noeuds, 3) : w, u, θ
    effort_normal: np.ndarray  # (nb_elements, 2) : (début, fin) [N]
    effort_tranchant: np.ndarray  # (nb_elements, 2) [N]
    moment_flechissant: np.ndarray  # (nb_elements, 2) [N·m]


def resoudre(
    maillage: Maillage,
    ea: Sequence[float],
    ei: Sequence[float],
    appuis: ConditionsAppui,
    sol: Sol,
    geometrie: Geometrie,
    forces_nodales: Sequence[float] | np.ndarray,
) -> ResultatMecanique:
    """Assemble, applique les conditions d'appui, résout et recompose N/V/M par élément."""
    K = assembler(maillage, ea, ei)

    k_ressort = rigidite_ressort_pied(appuis, sol, geometrie)
    if k_ressort is not None:
        K[2, 2] += k_ressort  # θ du nœud pied (nœud 0) = DOF global 2

    F = np.asarray(forces_nodales, dtype=float)
    if F.shape != (maillage.nb_dof,):
        raise ValueError(f"forces_nodales doit avoir {maillage.nb_dof} valeurs (reçu {F.shape})")

    bloques = dofs_bloques(appuis, maillage)
    libres = [i for i in range(maillage.nb_dof) if i not in bloques]

    d = np.zeros(maillage.nb_dof)
    d[libres] = np.linalg.solve(K[np.ix_(libres, libres)], F[libres])

    n_el = maillage.nb_elements
    effort_normal = np.zeros((n_el, 2))
    effort_tranchant = np.zeros((n_el, 2))
    moment_flechissant = np.zeros((n_el, 2))
    for i in range(n_el):
        dofs = list(maillage.dofs_element(i))
        q = k_element(ea[i], ei[i], maillage.longueur_element(i)) @ d[dofs]
        effort_normal[i] = (-q[0], q[3])
        effort_tranchant[i] = (-q[1], q[4])
        moment_flechissant[i] = (q[2], -q[5])

    deplacements = d.reshape(maillage.nb_noeuds, 3)
    for tableau in (deplacements, effort_normal, effort_tranchant, moment_flechissant):
        tableau.setflags(write=False)

    return ResultatMecanique(maillage, deplacements, effort_normal, effort_tranchant, moment_flechissant)
