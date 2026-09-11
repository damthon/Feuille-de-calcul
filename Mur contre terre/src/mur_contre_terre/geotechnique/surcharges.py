"""Pressions latérales dues aux surcharges du terre-plein — formule élastique (Boussinesq).

Modèle approché (paroi rigide, sol élastique semi-infini) pour la charge
linéaire ; la charge surfacique s'obtient par intégration de la charge
linéaire sur la largeur de la bande chargée (superposition). Contrairement
à la poussée des terres (§4.3.2), ce n'est pas une clause SIA que l'on
vous a fournie : le modèle est à confirmer contre vos cas de référence
(lot 12), au même titre que la pression de compactage.
"""

from __future__ import annotations

import math

import numpy as np


def pression_charge_lineaire(intensite: float, distance: float, profondeur: float) -> float:
    """σh [Pa] due à une charge linéaire Q [N/m] parallèle au mur, à ``distance`` [m] du parement.

    σh(z) = (2·Q/π)·a²·z / (a²+z²)², a = distance, z = profondeur.
    """
    if distance <= 0:
        raise ValueError(f"distance doit être strictement positive (reçu {distance})")
    if profondeur < 0:
        raise ValueError(f"profondeur doit être positive ou nulle (reçu {profondeur})")
    a, z = distance, profondeur
    return (2.0 * intensite / math.pi) * (a**2 * z) / (a**2 + z**2) ** 2


def pression_charge_surfacique(
    intensite: float, distance: float, etendue: float, profondeur: float, subdivisions: int = 200
) -> float:
    """σh [Pa] due à une charge surfacique q [Pa] sur une bande [distance, distance+étendue].

    Intégration numérique de ``pression_charge_lineaire`` sur la largeur de
    la bande (chaque tranche dx se comporte comme une charge linéaire
    d'intensité q·dx).
    """
    if distance < 0:
        raise ValueError(f"distance doit être positive ou nulle (reçu {distance})")
    if etendue <= 0:
        raise ValueError(f"etendue doit être strictement positive (reçu {etendue})")
    if profondeur < 0:
        raise ValueError(f"profondeur doit être positive ou nulle (reçu {profondeur})")

    xs = np.linspace(distance, distance + etendue, subdivisions)
    xs_non_nulles = np.where(xs <= 0, np.finfo(float).eps, xs)
    valeurs = (2.0 * intensite / math.pi) * (xs_non_nulles**2 * profondeur) / (xs_non_nulles**2 + profondeur**2) ** 2
    return float(np.trapezoid(valeurs, xs))
