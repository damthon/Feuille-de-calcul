"""Pression hydrostatique côté terre.

Diagramme triangulaire depuis le niveau de nappe (``Sol.niveau_nappe``,
profondeur depuis la surface du terrain) jusqu'au pied du mur, réduit par
``Sol.facteur_reduction_ecoulement`` pour tenir compte de la perte de
charge liée à l'écoulement autour du pied.
"""

from __future__ import annotations

from mur_contre_terre.donnees.sol import Sol

GAMMA_EAU = 9.81e3  # N/m³


def pression_hydrostatique(sol: Sol, profondeur: float) -> float:
    """Pression hydrostatique [Pa] à la profondeur donnée (depuis la surface du terrain)."""
    if sol.niveau_nappe is None or profondeur <= sol.niveau_nappe:
        return 0.0
    return sol.facteur_reduction_ecoulement * GAMMA_EAU * (profondeur - sol.niveau_nappe)
