"""Combinaisons d'actions — SIA 260 §4.4.3.

Une combinaison fait tourner chaque action variable comme dominante à son
tour (γQ,1 à l'ELU, ψ1,1 à l'ELS), les autres actions variables intervenant
à ψ0 (ELU) ou ψ2 (ELS). Les facteurs partiels γ sont pré-remplis selon la
norme mais modifiables — voir ``generer_combinaisons_elu``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from mur_contre_terre.donnees.charges import CasDeCharge, CategorieAction

GAMMA_G_DEFAUT = 1.35  # SIA 260 tableau 3, action permanente défavorable
GAMMA_Q_DEFAUT = 1.5  # SIA 260 tableau 3, action variable


@dataclass(frozen=True)
class Combinaison:
    nom: str
    facteurs: Mapping[str, float]  # CasDeCharge.nom -> facteur multiplicatif

    def __post_init__(self) -> None:
        object.__setattr__(self, "facteurs", MappingProxyType(dict(self.facteurs)))


def generer_combinaisons_elu(
    charges: Sequence[CasDeCharge], gamma_g: float = GAMMA_G_DEFAUT, gamma_q: float = GAMMA_Q_DEFAUT
) -> tuple[Combinaison, ...]:
    """ELU type 2 : Σγg·Gk + γq,1·Qk,1 + Σγq,i·ψ0,i·Qk,i — une combinaison par action dominante."""
    permanentes = [c for c in charges if c.categorie is CategorieAction.G]
    variables = [c for c in charges if c.categorie is CategorieAction.Q]
    base = {c.nom: gamma_g for c in permanentes}
    if not variables:
        return (Combinaison("ELU", dict(base)),)
    combinaisons = []
    for dominante in variables:
        facteurs = dict(base)
        facteurs[dominante.nom] = gamma_q
        for autre in variables:
            if autre is not dominante:
                facteurs[autre.nom] = gamma_q * autre.psi0
        combinaisons.append(Combinaison(f"ELU — {dominante.nom} dominante", facteurs))
    return tuple(combinaisons)


def generer_combinaisons_els(charges: Sequence[CasDeCharge]) -> tuple[Combinaison, ...]:
    """ELS fréquent : ΣGk + ψ1,1·Qk,1 + Σψ2,i·Qk,i — une combinaison par action dominante."""
    permanentes = [c for c in charges if c.categorie is CategorieAction.G]
    variables = [c for c in charges if c.categorie is CategorieAction.Q]
    base = {c.nom: 1.0 for c in permanentes}
    if not variables:
        return (Combinaison("ELS", dict(base)),)
    combinaisons = []
    for dominante in variables:
        facteurs = dict(base)
        facteurs[dominante.nom] = dominante.psi1
        for autre in variables:
            if autre is not dominante:
                facteurs[autre.nom] = autre.psi2
        combinaisons.append(Combinaison(f"ELS — {dominante.nom} dominante", facteurs))
    return tuple(combinaisons)


def vecteur_combine(combinaison: Combinaison, vecteurs_par_charge: Mapping[str, np.ndarray]) -> np.ndarray:
    """Somme pondérée des vecteurs de charges nodales selon les facteurs de la combinaison."""
    total: np.ndarray | None = None
    for nom, facteur in combinaison.facteurs.items():
        if nom not in vecteurs_par_charge:
            raise KeyError(f"Aucun vecteur de charge nodale fourni pour {nom!r}")
        contribution = facteur * vecteurs_par_charge[nom]
        total = contribution if total is None else total + contribution
    if total is None:
        raise ValueError("Combinaison sans aucun facteur")
    return total
