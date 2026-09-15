"""Moment-courbure M-χ(N) et rigidité sécante EI — armature fixe, N maintenu constant.

Contrairement à ``flexion_composee.py`` (qui *dimensionne* l'armature
nécessaire pour un état limite ultime donné, fibre extrême comprimée
fixée à −εcu), ce module trace la relation M-χ complète, à effort
normal N constant et armature *donnée* (deux lits fixes), depuis une
courbure quasi nulle jusqu'à la rupture (écrasement du béton à −εcu ou
rupture de l'acier à ±εud, le premier atteint). Il alimente le solveur
incrémental non linéaire du lot 7 (``nonlineaire/solveur_incremental.py``),
qui a besoin d'une rigidité sécante EI(x) = M(x)/χ(x) mise à jour à
chaque palier de charge le long de la hauteur du mur.

Même repère et même convention de signe que ``flexion_composee.py``
(voir son en-tête) : ``z = 0`` côté terre, ``z = h`` côté intérieur,
déformation ``ε(z) = ε0 + χ·(z − h/2)`` positive en traction. Avec cette
définition, ``χ > 0`` tend systématiquement la face intérieure (M > 0,
même convention que ``flexion_composee``) et ``χ < 0`` la face terre —
c'est le paramètre ``sens`` (+1/−1) qui choisit la direction de flexion
tracée, pas un argument ``face_tendue`` séparé.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from mur_contre_terre.donnees.materiaux import Materiaux
from mur_contre_terre.section_ba.flexion_composee import SectionRectangulaire
from mur_contre_terre.section_ba.modele_acier import contrainte_acier
from mur_contre_terre.section_ba.modele_beton import contrainte_beton

N_FIBRES = 200  # intervalles d'intégration numérique (trapèzes) sur la hauteur de la section
_EPS0_BORNE = 1.0  # borne large de recherche sur epsilon0 (bissection) — les lois de matériaux bornent la contrainte bien avant
_MAX_DOUBLEMENTS = 80  # scan géométrique pour encadrer la courbure de rupture


def _trapezes(valeurs: np.ndarray, z: np.ndarray) -> float:
    """Intégrale ∫ valeurs dz par la règle des trapèzes (voir la même note dans flexion_composee.py)."""
    return float(np.sum((valeurs[:-1] + valeurs[1:]) * np.diff(z)) / 2.0)


@dataclass(frozen=True)
class PointMomentCourbure:
    chi: float  # courbure [1/m]
    m: float  # moment résistant [N·m]
    ei_secant: float  # EI sécant = M/χ [N·m²]
    eps_terre: float  # déformation au lit d'armature côté terre
    eps_interieur: float  # déformation au lit d'armature côté intérieur


def _etat(
    eps0: float,
    chi: float,
    section: SectionRectangulaire,
    materiaux: Materiaux,
    armature_terre: float,
    armature_interieur: float,
    calcul: bool,
) -> tuple[float, float, float, float, float, float]:
    """(N, M, ε(0), ε(h), ε_terre, ε_interieur) pour un état de déformation (ε0, χ) donné."""
    h = section.epaisseur
    z = np.linspace(0.0, h, N_FIBRES + 1)
    eps = eps0 + chi * (z - h / 2.0)
    sigma = np.array([contrainte_beton(e, materiaux.beton, calcul) for e in eps])
    fc = section.largeur * _trapezes(sigma, z)
    mc = section.largeur * _trapezes(sigma * (z - h / 2.0), z)

    z_t, z_i = section.z_armature_terre, section.z_armature_interieur
    eps_t = eps0 + chi * (z_t - h / 2.0)
    eps_i = eps0 + chi * (z_i - h / 2.0)
    sigma_t = contrainte_acier(eps_t, materiaux.acier, calcul)
    sigma_i = contrainte_acier(eps_i, materiaux.acier, calcul)

    n = fc + armature_terre * sigma_t + armature_interieur * sigma_i
    m = mc + armature_terre * sigma_t * (z_t - h / 2.0) + armature_interieur * sigma_i * (z_i - h / 2.0)
    return n, m, float(eps[0]), float(eps[-1]), eps_t, eps_i


def _resoudre_eps0(
    n_ed: float,
    chi: float,
    section: SectionRectangulaire,
    materiaux: Materiaux,
    armature_terre: float,
    armature_interieur: float,
) -> tuple[float, float, float, float, float, float]:
    """(ε0, N, M, ε(0), ε(h), ε_terre, ε_interieur) équilibrant N_Ed à χ donné — bissection sur ε0.

    N(ε0) est croissant (ou constant par paliers) avec ε0 : les lois de
    matériaux sont monotones non décroissantes en déformation.
    """
    bas, haut = -_EPS0_BORNE, _EPS0_BORNE
    n_bas = _etat(bas, chi, section, materiaux, armature_terre, armature_interieur, True)[0]
    n_haut = _etat(haut, chi, section, materiaux, armature_terre, armature_interieur, True)[0]
    if not n_bas <= n_ed <= n_haut:
        raise ValueError(f"N_Ed={n_ed} hors de la capacité de la section à χ={chi} (bornes [{n_bas}, {n_haut}])")

    for _ in range(80):
        milieu = 0.5 * (bas + haut)
        n_milieu = _etat(milieu, chi, section, materiaux, armature_terre, armature_interieur, True)[0]
        if n_milieu < n_ed:
            bas = milieu
        else:
            haut = milieu

    eps0 = 0.5 * (bas + haut)
    n, m, eps_0, eps_h, eps_t, eps_i = _etat(eps0, chi, section, materiaux, armature_terre, armature_interieur, True)
    return eps0, n, m, eps_0, eps_h, eps_t, eps_i


def _depassement(
    eps_0: float, eps_h: float, eps_t: float, eps_i: float, materiaux: Materiaux
) -> float:
    """> 0 dès qu'une limite de déformation est dépassée (écrasement du béton ou rupture de l'acier)."""
    eps_cu = materiaux.beton.epsilon_cu
    eps_ud = materiaux.acier.epsilon_ud
    return max(
        -eps_cu - eps_0,
        -eps_cu - eps_h,
        abs(eps_t) - eps_ud,
        abs(eps_i) - eps_ud,
    )


def courbure_ultime(
    n_ed: float,
    section: SectionRectangulaire,
    materiaux: Materiaux,
    armature_terre: float,
    armature_interieur: float,
    sens: int = 1,
) -> float:
    """χ_ultime — première courbure (dans la direction ``sens`` = ±1) où une déformation limite est atteinte."""
    if sens not in (1, -1):
        raise ValueError(f"sens doit être 1 ou -1 (reçu {sens})")

    _, _, _, eps_0, eps_h, eps_t, eps_i = _resoudre_eps0(n_ed, 0.0, section, materiaux, armature_terre, armature_interieur)
    if _depassement(eps_0, eps_h, eps_t, eps_i, materiaux) > 0.0:
        raise ValueError(
            f"N_Ed={n_ed} dépasse déjà la capacité de la section en compression/traction pure (χ=0)."
        )

    chi_bas = 0.0
    chi = sens * 1e-5
    for _ in range(_MAX_DOUBLEMENTS):
        _, _, _, eps_0, eps_h, eps_t, eps_i = _resoudre_eps0(
            n_ed, chi, section, materiaux, armature_terre, armature_interieur
        )
        if _depassement(eps_0, eps_h, eps_t, eps_i, materiaux) >= 0.0:
            chi_haut = chi
            break
        chi_bas = chi
        chi *= 2.0
    else:
        raise ValueError("Courbure de rupture non trouvée dans le domaine de recherche — cas hors de portée du modèle.")

    for _ in range(60):
        chi_milieu = 0.5 * (chi_bas + chi_haut)
        _, _, _, eps_0, eps_h, eps_t, eps_i = _resoudre_eps0(
            n_ed, chi_milieu, section, materiaux, armature_terre, armature_interieur
        )
        if _depassement(eps_0, eps_h, eps_t, eps_i, materiaux) >= 0.0:
            chi_haut = chi_milieu
        else:
            chi_bas = chi_milieu

    return chi_haut


def courbe_moment_courbure(
    n_ed: float,
    section: SectionRectangulaire,
    materiaux: Materiaux,
    armature_terre: float,
    armature_interieur: float,
    sens: int = 1,
    nb_paliers: int = 20,
) -> tuple[PointMomentCourbure, ...]:
    """Courbe M-χ(N) en ``nb_paliers`` points réguliers entre 0 (exclu) et la courbure de rupture."""
    if nb_paliers < 1:
        raise ValueError(f"nb_paliers doit être strictement positif (reçu {nb_paliers})")

    chi_ultime = courbure_ultime(n_ed, section, materiaux, armature_terre, armature_interieur, sens)

    points = []
    for i in range(1, nb_paliers + 1):
        chi = chi_ultime * i / nb_paliers
        _, _, m, _, _, eps_t, eps_i = _resoudre_eps0(n_ed, chi, section, materiaux, armature_terre, armature_interieur)
        points.append(PointMomentCourbure(chi=chi, m=m, ei_secant=m / chi, eps_terre=eps_t, eps_interieur=eps_i))
    return tuple(points)


def rigidite_non_fissuree(section: SectionRectangulaire, materiaux: Materiaux) -> float:
    """EI de la section brute non fissurée (Ecm·b·h³/12) — même approximation que ``mecanique/rigidite.py``.

    Sert de valeur de départ (palier de charge quasi nul) au solveur
    incrémental, avant que la courbe M-χ ne devienne significative.
    """
    b, h = section.largeur, section.epaisseur
    return materiaux.beton.Ecm * b * h**3 / 12.0
