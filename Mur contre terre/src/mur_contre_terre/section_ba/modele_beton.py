"""Loi contrainte-déformation du béton — SIA 262 §4.1 (harmonisé EN 1992-1-1 §3.1.7).

Parabole-rectangle en compression (exposant n=2, déformation au pic
``EPS_C2``, plateau jusqu'à ``Beton.epsilon_cu``) ; traction linéaire
(module ``Ecm``) jusqu'à fissuration (``fctm``), nulle au-delà — le béton
fissuré ne reprend aucune traction résiduelle (pas de tension stiffening).

Convention de signe : déformation et contrainte positives en traction,
cohérente avec N/M du reste du paquet (voir l'en-tête de
``mecanique/solveur_lineaire.py``). Toutes les fonctions sont pures et
vectorisées (``epsilon`` scalaire ou tableau numpy — l'intégration par
fibres de ``flexion_composee.py``/``moment_courbure.py`` en dépend pour
rester praticable dans les bissections imbriquées du solveur
incrémental, lot 7).
"""

from __future__ import annotations

import numpy as np

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


def contrainte_beton(epsilon, beton: Beton, calcul: bool = True):
    """σ(ε) [Pa], positif en traction — ``epsilon`` scalaire ou tableau numpy.

    ``calcul=True`` (par défaut) utilise la résistance de calcul fcd =
    fck/γc (vérification ELU) ; ``calcul=False`` utilise fck directement
    (valeur caractéristique, pour une estimation de rigidité en service).

    La déformation est bornée en interne au domaine admissible
    (]-epsilon_cu, +∞[ en pratique tronqué au plateau parabole-rectangle
    côté compression) pour rester robuste dans une recherche itérative
    d'équilibre (``flexion_composee.py``) ; la validité de l'état de
    déformation final est du ressort de l'appelant.
    """
    scalaire = np.ndim(epsilon) == 0
    eps_signe = np.asarray(epsilon, dtype=float)

    eps_fiss = deformation_fissuration(beton)
    sigma_traction = np.where(eps_signe < eps_fiss, beton.Ecm * eps_signe, 0.0)

    eps_compression = np.clip(-eps_signe, 0.0, beton.epsilon_cu)  # compression positive, tronquée à epsilon_cu
    resistance = fcd(beton) if calcul else beton.fck
    sigma_compression = -np.where(
        eps_compression <= EPS_C2,
        resistance * (1.0 - (1.0 - eps_compression / EPS_C2) ** N_PARABOLE),
        resistance,
    )

    sigma = np.where(eps_signe >= 0.0, sigma_traction, sigma_compression)
    return float(sigma) if scalaire else sigma
