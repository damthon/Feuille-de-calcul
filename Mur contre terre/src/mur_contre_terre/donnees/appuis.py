"""Conditions d'appui du mur.

Pied : encastrement parfait (défaut) ou encastrement élastique par ressort
en rotation kθ = ks·B³/12 (modèle de Winkler, §6 du plan de conception).
Tête : libre ou appuyée horizontalement par la dalle.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TypeAppuiPied(Enum):
    ENCASTREMENT = "encastrement"
    RESSORT = "ressort"


class TypeAppuiTete(Enum):
    LIBRE = "libre"
    APPUI_DALLE = "appui_dalle"


@dataclass(frozen=True)
class ConditionsAppui:
    pied: TypeAppuiPied = TypeAppuiPied.ENCASTREMENT
    tete: TypeAppuiTete = TypeAppuiTete.LIBRE
    k_theta: float | None = None
    """N·m/rad par mètre de mur. ``None`` => calculé automatiquement à
    partir de Sol.ks et Geometrie.largeur_semelle quand pied=RESSORT."""

    def __post_init__(self) -> None:
        if self.pied is TypeAppuiPied.ENCASTREMENT and self.k_theta is not None:
            raise ValueError("k_theta n'a pas de sens pour un encastrement parfait")
        if self.k_theta is not None and self.k_theta <= 0:
            raise ValueError(f"ConditionsAppui.k_theta doit être strictement positif (reçu {self.k_theta})")
