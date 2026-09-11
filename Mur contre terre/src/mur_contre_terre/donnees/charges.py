"""Cas de charge — SIA 261 §5.3 du plan de conception.

Chaque charge porte sa catégorie d'action, sa valeur caractéristique (en
unités SI) et ses coefficients ψ. Les paramètres propres à chaque type de
charge (excentricité, étendue, distance au mur, profondeur d'application…)
vivent dans ``parametres``, une petite table libre plutôt qu'un champ par
type — les types de charge n'ont pas tous les mêmes paramètres.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping


class CategorieAction(Enum):
    G = "G"
    Q = "Q"
    A = "A"


class TypeCharge(Enum):
    POIDS_PROPRE = "poids_propre"
    CHARGE_TETE = "charge_tete"
    POUSSEE_TERRES = "poussee_terres"
    SURCHARGE_TETE = "surcharge_tete"
    CHARGE_SURFACIQUE_TERREPLEIN = "charge_surfacique_terreplein"
    CHARGE_LINEAIRE_TERREPLEIN = "charge_lineaire_terreplein"
    PRESSION_HYDROSTATIQUE = "pression_hydrostatique"
    PRESSION_COMPACTAGE = "pression_compactage"


@dataclass(frozen=True)
class CasDeCharge:
    nom: str
    type: TypeCharge
    categorie: CategorieAction
    valeur: float
    psi0: float = 0.0
    psi1: float = 0.0
    psi2: float = 0.0
    parametres: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "parametres", MappingProxyType(dict(self.parametres)))
        for nom in ("psi0", "psi1", "psi2"):
            valeur = getattr(self, nom)
            if not 0.0 <= valeur <= 1.0:
                raise ValueError(f"CasDeCharge.{nom} doit être dans [0, 1] (reçu {valeur})")
