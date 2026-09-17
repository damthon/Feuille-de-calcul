"""Pression hydrostatique côté terre.

Diagramme triangulaire depuis le niveau de nappe (``Sol.niveau_nappe``,
hauteur du plan d'eau depuis le pied du mur) jusqu'au pied du mur, réduit par
``Sol.facteur_reduction_ecoulement`` pour tenir compte de la perte de
charge liée à l'écoulement autour du pied.
"""

from __future__ import annotations

from mur_contre_terre.donnees.sol import Sol

GAMMA_EAU = 9.81e3  # N/m³


def pression_hydrostatique(sol: Sol, hauteur: float, profondeur: float) -> float:
    """Pression hydrostatique [Pa] à la profondeur donnée (depuis la surface du terrain). ``sol.niveau_nappe``
    est la hauteur du plan d'eau depuis le pied du mur — convertie ici en profondeur depuis la surface
    (``hauteur - niveau_nappe``) pour la comparer à ``profondeur``."""
    if sol.niveau_nappe is None:
        return 0.0
    profondeur_nappe = hauteur - sol.niveau_nappe
    if profondeur <= profondeur_nappe:
        return 0.0
    return sol.facteur_reduction_ecoulement * GAMMA_EAU * (profondeur - profondeur_nappe)
