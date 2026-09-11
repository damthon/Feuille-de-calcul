"""Conversions d'unités aux frontières du modèle.

Toutes les grandeurs internes du paquet sont en unités SI strictes
(mètre, newton, pascal, radian, seconde). Les entrées d'un projet
d'ingénierie s'expriment naturellement en kN, kNm, MPa, kN/m2, kN/m3 et
degrés : les fonctions ci-dessous font la conversion une fois, à la
construction des objets de ``donnees``, jamais à l'intérieur d'un calcul.
"""

from __future__ import annotations

import math

__all__ = [
    "kN", "kNm", "MPa", "kN_m2", "kN_m3", "deg",
    "en_kN", "en_kNm", "en_MPa", "en_kN_m2", "en_kN_m3", "en_deg",
]


def kN(valeur: float) -> float:
    """kN vers N."""
    return valeur * 1e3


def kNm(valeur: float) -> float:
    """kNm vers N·m."""
    return valeur * 1e3


def MPa(valeur: float) -> float:
    """MPa vers Pa."""
    return valeur * 1e6


def kN_m2(valeur: float) -> float:
    """kN/m² vers Pa."""
    return valeur * 1e3


def kN_m3(valeur: float) -> float:
    """kN/m³ vers N/m³."""
    return valeur * 1e3


def deg(valeur: float) -> float:
    """Degrés vers radians."""
    return math.radians(valeur)


def en_kN(valeur_n: float) -> float:
    """N vers kN."""
    return valeur_n / 1e3


def en_kNm(valeur_nm: float) -> float:
    """N·m vers kNm."""
    return valeur_nm / 1e3


def en_MPa(valeur_pa: float) -> float:
    """Pa vers MPa."""
    return valeur_pa / 1e6


def en_kN_m2(valeur_pa: float) -> float:
    """Pa vers kN/m²."""
    return valeur_pa / 1e3


def en_kN_m3(valeur_n_m3: float) -> float:
    """N/m³ vers kN/m³."""
    return valeur_n_m3 / 1e3


def en_deg(valeur_rad: float) -> float:
    """Radians vers degrés."""
    return math.degrees(valeur_rad)
