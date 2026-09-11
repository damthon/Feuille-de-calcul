"""Maillage aux éléments finis de la paroi.

``z`` se compte depuis le pied (0) jusqu'au couronnement (``hauteur``) —
même convention que ``Geometrie.epaisseur``. 3 degrés de liberté par nœud,
dans l'ordre [w (axial, vertical), u (transversal, horizontal), θ
(rotation)] ; le nœud ``i`` occupe les degrés de liberté globaux
``3i, 3i+1, 3i+2``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from mur_contre_terre.donnees.geometrie import Geometrie

DOF_PAR_NOEUD = 3


@dataclass(frozen=True)
class Maillage:
    positions: tuple[float, ...]  # z croissant, 0 (pied) à hauteur (tête)

    def __post_init__(self) -> None:
        if len(self.positions) < 2:
            raise ValueError("Maillage.positions doit contenir au moins 2 nœuds")
        if any(b <= a for a, b in zip(self.positions, self.positions[1:])):
            raise ValueError("Maillage.positions doit être strictement croissant")

    @property
    def nb_noeuds(self) -> int:
        return len(self.positions)

    @property
    def nb_elements(self) -> int:
        return len(self.positions) - 1

    @property
    def nb_dof(self) -> int:
        return DOF_PAR_NOEUD * self.nb_noeuds

    def longueur_element(self, i: int) -> float:
        return self.positions[i + 1] - self.positions[i]

    def milieu_element(self, i: int) -> float:
        return 0.5 * (self.positions[i] + self.positions[i + 1])

    def dofs_element(self, i: int) -> range:
        """Degrés de liberté globaux de l'élément ``i`` (contigus : nœuds i et i+1)."""
        debut = DOF_PAR_NOEUD * i
        return range(debut, debut + 2 * DOF_PAR_NOEUD)


def generer_maillage(geometrie: Geometrie, finesse: float) -> Maillage:
    """Maillage régulier de la hauteur du mur, éléments de longueur ≤ ``finesse``."""
    if finesse <= 0:
        raise ValueError(f"finesse doit être strictement positive (reçu {finesse})")
    nb_elements = max(1, math.ceil(geometrie.hauteur / finesse))
    pas = geometrie.hauteur / nb_elements
    positions = tuple(i * pas for i in range(nb_elements + 1))
    return Maillage(positions)
