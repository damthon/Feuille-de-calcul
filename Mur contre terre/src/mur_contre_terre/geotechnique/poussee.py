"""Poussée des terres — SIA 261 §4.3.2 (méthode de Coulomb).

Toutes les fonctions sont pures : elles prennent des angles en radians, des
contraintes en pascals, et ne connaissent ni ``Geometrie`` ni ``Projet``.
La profondeur ``profondeur`` se compte depuis la surface du terrain côté
terre (0 en tête du mur, ``hauteur`` au pied) — c'est l'axe naturel des
formules normatives (Σγe,k·Δz). Le maillage mécanique (lot 3) utilisera la
convention inverse (``z`` = 0 au pied) et fera la conversion
``profondeur = hauteur - z``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from mur_contre_terre.donnees.sol import Sol, TypePoussee
from mur_contre_terre.geotechnique.hydrostatique import GAMMA_EAU

E_AH_MIN = 5.0e3  # Pa — poussée active minimale en sol cohérent, SIA 261 §4.3.2.2


def delta_actif_defaut(phi: float, rugueux: bool = True) -> float:
    """δk par défaut pour la poussée active — SIA 261 §4.3.2.3, Figure 1."""
    return 2.0 * phi / 3.0 if rugueux else 0.0


def kah_coulomb(phi: float, delta: float, beta: float = 0.0, alpha: float = math.pi / 2) -> float:
    """Coefficient de poussée active de Coulomb Kah.

    ``alpha`` est l'inclinaison du parement (π/2 = mur vertical, cas
    courant ici). δ = 0 et β = 0 redonnent la formule de Rankine.
    """
    if beta > phi:
        raise ValueError(f"beta ({beta} rad) doit être ≤ phi ({phi} rad) — SIA 261 §4.3.2.4")
    if not 0.0 < alpha - delta < math.pi:
        raise ValueError("alpha - delta doit être dans ]0, π[")
    if not -math.pi / 2 < alpha + beta < math.pi:
        raise ValueError("alpha + beta hors du domaine de validité de la formule")

    terme = math.sqrt(
        (math.sin(phi + delta) * math.sin(phi - beta))
        / (math.sin(alpha - delta) * math.sin(alpha + beta))
    )
    denominateur = math.sin(alpha) ** 2 * math.sin(alpha - delta) * (1.0 + terme) ** 2
    return math.sin(alpha + phi) ** 2 / denominateur


def k0_jaky(phi: float, beta: float = 0.0) -> float:
    """Coefficient de poussée au repos K0 — SIA 261 §4.3.2.4, éq. (5).

    β = 0 redonne la formule de Jaky classique K0 = 1 − sin(φ′).
    """
    if abs(beta) > phi:
        raise ValueError(f"|beta| ({beta} rad) doit être ≤ phi ({phi} rad) — SIA 261 §4.3.2.4")
    return (1.0 - math.sin(phi)) * (1.0 + math.sin(beta)) / math.cos(beta)


@dataclass(frozen=True)
class CoefficientsPoussee:
    kah: float | None  # poussée active ; None si au repos
    k0: float | None  # poussée au repos ; None si active
    delta: float  # δk effectif (saisi ou par défaut)

    @property
    def k(self) -> float:
        return self.kah if self.kah is not None else self.k0  # type: ignore[return-value]


def coefficients_poussee(sol: Sol) -> CoefficientsPoussee:
    """Coefficient de poussée et δ effectif pour le type de poussée choisi dans ``sol``."""
    delta = sol.delta if sol.delta is not None else delta_actif_defaut(sol.phi, sol.rugueux)
    if sol.type_poussee is TypePoussee.ACTIF:
        return CoefficientsPoussee(kah=kah_coulomb(sol.phi, delta, sol.beta), k0=None, delta=delta)
    return CoefficientsPoussee(kah=None, k0=k0_jaky(sol.phi, sol.beta), delta=delta)


def contrainte_verticale_effective(sol: Sol, hauteur: float, profondeur: float, g0: float = 0.0) -> float:
    """σ'v(z) — contrainte verticale effective à la profondeur donnée, surcharge g0 [Pa] en tête comprise.

    Tient compte du poids déjaugé sous la nappe (``Sol.gamma_sat`` réduit du
    poids volumique de l'eau) ; la pression d'eau elle-même est calculée
    séparément (``hydrostatique.pression_hydrostatique``).
    """
    if not 0.0 <= profondeur <= hauteur:
        raise ValueError(f"profondeur={profondeur} hors de la hauteur du mur [0, {hauteur}]")
    if sol.niveau_nappe is None or profondeur <= sol.niveau_nappe:
        return g0 + sol.gamma * profondeur
    gamma_prime = sol.gamma_sat - GAMMA_EAU  # type: ignore[operator]
    return g0 + sol.gamma * sol.niveau_nappe + gamma_prime * (profondeur - sol.niveau_nappe)


def pression_verticale(e_ah: float, sol: Sol, delta: float) -> float:
    """e_av,k — composante verticale de la poussée, SIA 261 §4.3.2.3 éq. (4).

    Pour la poussée active, la résultante est inclinée de δk sur la
    normale au parement (e_av,k = e_ah,k·tan δk). Pour la poussée au repos,
    la norme retient une résultante parallèle à la pente du terrain
    (e_av,k = e_ah,k·tan β), indépendamment de δ.
    """
    angle = delta if sol.type_poussee is TypePoussee.ACTIF else sol.beta
    return e_ah * math.tan(angle)


def pression_active_horizontale(sol: Sol, hauteur: float, profondeur: float, g0: float = 0.0) -> float:
    """e_ah,k — SIA 261 §4.3.2.3 éq. (3), avec le plancher de §4.3.2.2 si c′k > 0."""
    coeffs = coefficients_poussee(sol)
    if coeffs.kah is None:
        raise ValueError("pression_active_horizontale requiert Sol.type_poussee == ACTIF")
    sigma_v = contrainte_verticale_effective(sol, hauteur, profondeur, g0)
    if sol.c <= 0.0:
        return coeffs.kah * sigma_v
    brute = coeffs.kah * sigma_v - 2.0 * sol.c * math.sqrt(coeffs.kah)
    return max(brute, E_AH_MIN)


def profil_poussee(sol: Sol, hauteur: float, profondeur: float, g0: float = 0.0) -> tuple[float, float]:
    """Couple (e_ah,k, e_av,k) [Pa] à la profondeur donnée, poussée active ou au repos selon ``sol``."""
    coeffs = coefficients_poussee(sol)
    sigma_v = contrainte_verticale_effective(sol, hauteur, profondeur, g0)
    if coeffs.kah is not None:
        if sol.c > 0.0:
            brute = coeffs.kah * sigma_v - 2.0 * sol.c * math.sqrt(coeffs.kah)
            e_ah = max(brute, E_AH_MIN)
        else:
            e_ah = coeffs.kah * sigma_v
    else:
        e_ah = coeffs.k0 * sigma_v  # type: ignore[operator]
    e_av = pression_verticale(e_ah, sol, coeffs.delta)
    return e_ah, e_av
