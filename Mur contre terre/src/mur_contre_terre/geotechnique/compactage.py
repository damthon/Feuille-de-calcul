"""Pression de compactage — SIA 261 §5.3 du plan de conception.

Modèle simplifié conforme aux deux seuls paramètres demandés dans le cahier
des charges (intensité, profondeur d'application) : plateau de pression
constant sur les ``profondeur_application`` premiers mètres depuis la
surface, nul au-delà. Un profil enveloppe plus détaillé (croissance
linéaire puis plateau, type Broms/OCDI) pourra remplacer ce modèle si une
clause SIA 267 précise est fournie — à confirmer au lot 12 contre vos cas
de référence.
"""

from __future__ import annotations


def pression_compactage(intensite: float, profondeur_application: float, profondeur: float) -> float:
    """Pression de compactage [Pa] à la profondeur donnée (depuis la surface du terrain)."""
    if profondeur_application < 0:
        raise ValueError(f"profondeur_application doit être positive ou nulle (reçu {profondeur_application})")
    if profondeur < 0:
        raise ValueError(f"profondeur doit être positive ou nulle (reçu {profondeur})")
    return intensite if profondeur <= profondeur_application else 0.0
