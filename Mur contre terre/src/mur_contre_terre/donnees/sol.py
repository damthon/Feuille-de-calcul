"""Paramètres du sol et de la poussée des terres — SIA 261 §4.3.2 / SIA 267.

Angles en radians, cohésion et module de réaction en pascals, poids
volumiques en N/m³ (voir ``unites.py`` pour construire ces valeurs depuis
des degrés, kPa et kN/m³). Les coefficients de poussée (Kah, Kph, K0) et
les valeurs par défaut de δ ne sont pas calculés ici : ``Sol`` ne porte que
les données, le calcul revient au module ``geotechnique.poussee`` (lot 2).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TypePoussee(Enum):
    ACTIF = "actif"
    AU_REPOS = "au_repos"


@dataclass(frozen=True)
class Sol:
    gamma: float
    phi: float
    c: float = 0.0
    beta: float = 0.0
    gamma_sat: float | None = None
    delta: float | None = None
    rugueux: bool = True
    type_poussee: TypePoussee = TypePoussee.ACTIF
    niveau_nappe: float | None = None
    facteur_reduction_ecoulement: float = 1.0
    ks: float | None = None

    def __post_init__(self) -> None:
        if self.gamma <= 0:
            raise ValueError(f"Sol.gamma doit être strictement positif (reçu {self.gamma})")
        if not 0.0 < self.phi < 1.5708:
            raise ValueError(f"Sol.phi doit être dans ]0, π/2[ radians (reçu {self.phi})")
        if self.c < 0:
            raise ValueError(f"Sol.c doit être positif ou nul (reçu {self.c})")
        if self.gamma_sat is not None and self.gamma_sat <= 0:
            raise ValueError(f"Sol.gamma_sat doit être strictement positif (reçu {self.gamma_sat})")
        if self.niveau_nappe is not None and self.gamma_sat is None:
            raise ValueError("Sol.gamma_sat est requis dès qu'un niveau de nappe est défini")
        if not 0.0 < self.facteur_reduction_ecoulement <= 1.0:
            raise ValueError(
                "Sol.facteur_reduction_ecoulement doit être dans ]0, 1] "
                f"(reçu {self.facteur_reduction_ecoulement})"
            )
        if self.ks is not None and self.ks <= 0:
            raise ValueError(f"Sol.ks doit être strictement positif (reçu {self.ks})")
