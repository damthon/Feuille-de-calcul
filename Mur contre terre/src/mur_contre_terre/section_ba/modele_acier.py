"""Loi contrainte-déformation de l'acier d'armature — SIA 262 §4.1 (fig. 11).

Bilinéaire écrouissable, symétrique en traction et en compression : palier
élastique jusqu'à εyd = fsd/Es, puis droite d'écrouissage jusqu'à
(``Acier.epsilon_ud``, k·fsd) — k = ``Acier.k_durcissement``, classe de
ductilité B pour le B500B (k ≥ 1,08, εuk ≥ 45 ‰, SIA 262 tableau 26).

Convention de signe : déformation et contrainte positives en traction,
comme ``modele_beton.py``. Fonctions pures.
"""

from __future__ import annotations

import math

from mur_contre_terre.donnees.materiaux import Acier

GAMMA_S = 1.15  # SIA 262 tableau 25 / harmonisé EN 1992-1-1 tableau 2.1N


def fsd(acier: Acier, gamma_s: float = GAMMA_S) -> float:
    """Résistance de calcul fsd = fsk / γs [Pa]."""
    return acier.fsk / gamma_s


def deformation_elastique(acier: Acier, calcul: bool = True) -> float:
    """εyd (ou εyk si ``calcul=False``) — déformation à la limite élastique."""
    resistance = fsd(acier) if calcul else acier.fsk
    return resistance / acier.Es


def contrainte_acier(epsilon: float, acier: Acier, calcul: bool = True) -> float:
    """σ(ε) [Pa], positif en traction, symétrique en compression.

    ``calcul=True`` (par défaut) utilise fsd = fsk/γs (vérification ELU) ;
    ``calcul=False`` utilise fsk directement. La déformation est bornée en
    valeur absolue à ``Acier.epsilon_ud`` pour rester robuste dans une
    recherche itérative d'équilibre (``flexion_composee.py``) ; la
    ductilité effectivement mobilisée est du ressort de l'appelant.
    """
    resistance = fsd(acier) if calcul else acier.fsk
    eps_y = resistance / acier.Es
    eps = min(abs(epsilon), acier.epsilon_ud)

    if eps <= eps_y:
        sigma = acier.Es * eps
    else:
        pente = (acier.k_durcissement * resistance - resistance) / (acier.epsilon_ud - eps_y)
        sigma = resistance + pente * (eps - eps_y)

    return math.copysign(sigma, epsilon) if epsilon != 0.0 else 0.0
