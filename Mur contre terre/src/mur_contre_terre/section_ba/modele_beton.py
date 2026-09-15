"""Loi contrainte-déformation du béton — SIA 262 §4.1 (harmonisé EN 1992-1-1 §3.1.7).

Parabole-rectangle en compression (exposant n=2, déformation au pic
``EPS_C2``, plateau jusqu'à ``Beton.epsilon_cu``) ; traction linéaire
(module ``Ecm``) jusqu'à fissuration (``fctm``), nulle au-delà — le béton
fissuré ne reprend aucune traction résiduelle (pas de tension stiffening).

Convention de signe : déformation et contrainte positives en traction,
cohérente avec N/M du reste du paquet (voir l'en-tête de
``mecanique/solveur_lineaire.py``). Toutes les fonctions sont pures.
"""

from __future__ import annotations

from mur_contre_terre.donnees.materiaux import Beton

GAMMA_C = 1.5  # SIA 262 tableau 25 / harmonisé EN 1992-1-1 tableau 2.1N
EPS_C2 = 0.002  # déformation au pic de la parabole, béton de classe ≤ C50/60
N_PARABOLE = 2.0


def fcd(beton: Beton, gamma_c: float = GAMMA_C) -> float:
    """Résistance de calcul en compression fcd = fck / γc [Pa]."""
    return beton.fck / gamma_c


def deformation_fissuration(beton: Beton) -> float:
    """εct — déformation de traction à la fissuration, εct = fctm / Ecm."""
    return beton.fctm / beton.Ecm


def contrainte_beton(epsilon: float, beton: Beton, calcul: bool = True) -> float:
    """σ(ε) [Pa], positif en traction.

    ``calcul=True`` (par défaut) utilise la résistance de calcul fcd =
    fck/γc (vérification ELU) ; ``calcul=False`` utilise fck directement
    (valeur caractéristique, pour une estimation de rigidité en service).

    La déformation est bornée en interne au domaine admissible
    (]-epsilon_cu, +∞[ en pratique tronqué au plateau parabole-rectangle
    côté compression) pour rester robuste dans une recherche itérative
    d'équilibre (``flexion_composee.py``) ; la validité de l'état de
    déformation final est du ressort de l'appelant.
    """
    if epsilon >= 0.0:
        eps_fiss = deformation_fissuration(beton)
        if epsilon >= eps_fiss:
            return 0.0
        return beton.Ecm * epsilon

    eps = min(-epsilon, beton.epsilon_cu)  # compression positive pour la formule normative, tronquée à epsilon_cu
    resistance = fcd(beton) if calcul else beton.fck
    if eps <= EPS_C2:
        sigma = resistance * (1.0 - (1.0 - eps / EPS_C2) ** N_PARABOLE)
    else:
        sigma = resistance
    return -sigma
