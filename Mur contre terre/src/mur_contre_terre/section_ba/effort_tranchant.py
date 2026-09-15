"""Résistance à l'effort tranchant sans armature transversale — SIA 262 §4.3.3.

Aucun extrait normatif SIA 262 exact (formulation τcd/kd) n'a été fourni
pour ce lot — contrairement à la poussée des terres (§4.3.2, extrait
vérifié, voir ``geotechnique/poussee.py``). Le modèle retenu ci-dessous
est la formule harmonisée EN 1992-1-1 §6.2.2 (VRd,c), cohérente avec les
classes de béton déjà harmonisées dans ``donnees/materiaux.py``. **À
recouper avec le texte exact de la SIA 262 au lot 12**, comme la pression
de compactage et les charges de terre-plein (docs/plan-conception.html
§7-8) — un mur de sous-sol sans étriers est justement le cas où cette
vérification est dimensionnante, donc sensible à confirmer avant tout
usage réel.
"""

from __future__ import annotations

import math

from mur_contre_terre.donnees.materiaux import Beton
from mur_contre_terre.section_ba.modele_beton import GAMMA_C

C_RD_C = 0.18  # coefficient de base, à diviser par γc — EN 1992-1-1 §6.2.2 (1)
K1 = 0.15  # coefficient de l'effet favorable de la compression
V_MIN_COEF = 0.035  # coefficient de la résistance minimale (sections faiblement armées)
TAUX_ARMATURE_MAX = 0.02  # plafond normatif de ρl pris en compte dans la formule


def coefficient_taille(hauteur_utile: float) -> float:
    """k = 1 + √(0,2/d) ≤ 2,0 (d en mètres — équivalent à 1+√(200/d) avec d en mm)."""
    if hauteur_utile <= 0:
        raise ValueError(f"hauteur_utile doit être strictement positive (reçu {hauteur_utile})")
    return min(1.0 + math.sqrt(0.2 / hauteur_utile), 2.0)


def taux_armature_longitudinale(armature: float, largeur: float, hauteur_utile: float) -> float:
    """ρl = As / (b·d) — armature tendue supposée ancrée au-delà de la section considérée."""
    if largeur <= 0 or hauteur_utile <= 0:
        raise ValueError("largeur et hauteur_utile doivent être strictement positives")
    if armature < 0:
        raise ValueError(f"armature doit être positive ou nulle (reçu {armature})")
    return armature / (largeur * hauteur_utile)


def resistance_effort_tranchant(
    beton: Beton,
    largeur: float,
    hauteur_utile: float,
    taux_armature: float,
    effort_normal: float = 0.0,
    gamma_c: float = GAMMA_C,
) -> float:
    """V_Rd [N] — résistance à l'effort tranchant sans armature transversale.

    ``taux_armature`` = ρl = As/(b·d) (borné à ``TAUX_ARMATURE_MAX`` dans
    la formule, comme la norme le prescrit). ``effort_normal`` [N] suit la
    convention du paquet (positif en traction, voir
    ``mecanique/solveur_lineaire.py``) : seule une compression (N < 0) est
    valorisée dans σcp ; une traction (N > 0), défavorable, est ignorée
    par cette formule (σcp mis à 0) plutôt que de réduire artificiellement
    V_Rd — l'effet défavorable d'une traction axiale n'est pas couvert par
    ce modèle simplifié.
    """
    if largeur <= 0 or hauteur_utile <= 0:
        raise ValueError("largeur et hauteur_utile doivent être strictement positives")
    if taux_armature < 0.0:
        raise ValueError(f"taux_armature doit être positif ou nul (reçu {taux_armature})")

    k = coefficient_taille(hauteur_utile)
    rho = min(taux_armature, TAUX_ARMATURE_MAX)
    fck_mpa = beton.fck / 1.0e6
    sigma_cp_mpa = max(-effort_normal, 0.0) / (largeur * hauteur_utile) / 1.0e6
    sigma_cp_mpa = min(sigma_cp_mpa, 0.2 * fck_mpa / gamma_c)

    c_rd_c = C_RD_C / gamma_c
    v_rd_mpa = c_rd_c * k * (100.0 * rho * fck_mpa) ** (1.0 / 3.0) + K1 * sigma_cp_mpa
    v_min_mpa = V_MIN_COEF * k**1.5 * math.sqrt(fck_mpa) + K1 * sigma_cp_mpa
    v_rd_mpa = max(v_rd_mpa, v_min_mpa)

    return v_rd_mpa * 1.0e6 * largeur * hauteur_utile
