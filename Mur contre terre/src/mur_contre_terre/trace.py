"""Figures — géométrie, diagrammes N/V/M, moment-courbure, déformée (extra ``[trace]``, matplotlib).

Chaque fonction construit et retourne une ``matplotlib.figure.Figure``
sans l'afficher ni l'enregistrer — à l'appelant (CLI, interface de
bureau, export du rapport) de faire ``figure.savefig(...)`` ou de
l'intégrer à un canevas Tkinter (``FigureCanvasTkAgg``). Ce module
n'est importable que si l'extra ``matplotlib`` est installé
(``pip install -e ".[trace]"``) — dépendance volontairement non
obligatoire à l'exécution, comme le veut le plan de conception (§3).
"""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.mecanique.maillage import Maillage
from mur_contre_terre.mecanique.solveur_lineaire import ResultatMecanique
from mur_contre_terre.section_ba.moment_courbure import PointMomentCourbure
from mur_contre_terre.unites import en_kN, en_kNm


def figure_geometrie(geometrie: Geometrie) -> Figure:
    """Coupe schématique du mur : épaisseur interpolée entre la base et le couronnement, semelle avant."""
    fig, ax = plt.subplots(figsize=(4, 6))
    h = geometrie.hauteur
    # côté terre à gauche (x=0), face intérieure suit l'épaisseur locale
    z = np.linspace(0.0, h, 50)
    x_interieur = [geometrie.epaisseur(zi) for zi in z]
    contour_x = [0.0] + x_interieur + [0.0]
    contour_z = [0.0] + list(z) + [h]
    ax.fill(contour_x, contour_z, color="#ECE8DF", edgecolor="black", linewidth=1.2, zorder=2)

    # semelle avant (côté intérieur, débord)
    b = geometrie.debord_semelle
    x0 = geometrie.epaisseur(0.0)
    semelle_x = [0.0, x0 + b, x0 + b, 0.0]
    semelle_z = [0.0, 0.0, -geometrie.ep_semelle, -geometrie.ep_semelle]
    ax.fill(semelle_x, semelle_z, color="#ECE8DF", edgecolor="black", linewidth=1.2, zorder=2)

    ax.set_xlabel("épaisseur [m]")
    ax.set_ylabel("hauteur z [m]")
    ax.set_title("Géométrie du mur")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-0.3, x0 + b + 0.3)
    ax.set_ylim(-geometrie.ep_semelle - 0.2, h + 0.2)
    fig.tight_layout()
    return fig


def figure_diagramme(
    maillage: Maillage, valeurs: Sequence[float] | np.ndarray, titre: str, unite: str, facteur: float = 1.0
) -> Figure:
    """Diagramme d'une grandeur par nœud (déplacement, réaction…) le long de la hauteur du mur."""
    fig, ax = plt.subplots(figsize=(3.5, 6))
    z = maillage.positions
    v = np.asarray(valeurs, dtype=float) * facteur
    ax.plot(v, z, color="#1F4E63", linewidth=1.6)
    ax.axvline(0.0, color="black", linewidth=0.6)
    ax.set_xlabel(f"{titre} [{unite}]")
    ax.set_ylabel("hauteur z [m]")
    ax.set_title(titre)
    ax.invert_yaxis()
    fig.tight_layout()
    return fig


def figure_efforts(resultat: ResultatMecanique, titre_combinaison: str = "") -> Figure:
    """Diagrammes N(z), V(z), M(z) côte à côte pour un ``ResultatMecanique`` (une combinaison)."""
    fig, axes = plt.subplots(1, 3, figsize=(9, 6), sharey=True)
    # reconstruire une polyligne (début, fin) par élément pour un tracé continu par morceaux
    z_pts: list[float] = []
    n_pts: list[float] = []
    v_pts: list[float] = []
    m_pts: list[float] = []
    for i in range(resultat.maillage.nb_elements):
        z0, z1 = resultat.maillage.positions[i], resultat.maillage.positions[i + 1]
        z_pts += [z0, z1]
        n_pts += [en_kN(resultat.effort_normal[i, 0]), en_kN(resultat.effort_normal[i, 1])]
        v_pts += [en_kN(resultat.effort_tranchant[i, 0]), en_kN(resultat.effort_tranchant[i, 1])]
        m_pts += [en_kNm(resultat.moment_flechissant[i, 0]), en_kNm(resultat.moment_flechissant[i, 1])]

    for ax, valeurs, titre, unite in zip(axes, (n_pts, v_pts, m_pts), ("N", "V", "M"), ("kN", "kN", "kN·m")):
        ax.plot(valeurs, z_pts, color="#1F4E63", linewidth=1.6)
        ax.axvline(0.0, color="black", linewidth=0.6)
        ax.set_xlabel(f"{titre} [{unite}]")
        ax.set_title(titre)
    axes[0].set_ylabel("hauteur z [m]")
    axes[0].invert_yaxis()
    if titre_combinaison:
        fig.suptitle(titre_combinaison)
    fig.tight_layout()
    return fig


def figure_moment_courbure(points: Sequence[PointMomentCourbure]) -> Figure:
    """Courbe M(χ) — voir ``section_ba.moment_courbure.courbe_moment_courbure``."""
    fig, ax = plt.subplots(figsize=(5, 4))
    chi = [p.chi for p in points]
    m = [en_kNm(p.m) for p in points]
    ax.plot(chi, m, marker="o", markersize=3, color="#9C5A2E", linewidth=1.4)
    ax.axhline(0.0, color="black", linewidth=0.6)
    ax.axvline(0.0, color="black", linewidth=0.6)
    ax.set_xlabel("courbure χ [1/m]")
    ax.set_ylabel("moment M [kN·m]")
    ax.set_title("Moment-courbure")
    fig.tight_layout()
    return fig


def figure_deformee(maillage: Maillage, deplacements: np.ndarray, amplification: float = 1.0) -> Figure:
    """Déformée du mur (déplacement transversal u), amplifiée pour la lisibilité."""
    fig, ax = plt.subplots(figsize=(3.5, 6))
    z = maillage.positions
    u = deplacements[:, 1] * amplification * 1000.0  # mm
    ax.plot(np.zeros_like(z), z, color="#D9D3C6", linewidth=1.0, linestyle="--")
    ax.plot(u, z, color="#1F4E63", linewidth=1.8)
    ax.set_xlabel(f"déplacement u [mm] (× {amplification:g})")
    ax.set_ylabel("hauteur z [m]")
    ax.set_title("Déformée")
    fig.tight_layout()
    return fig


__all__ = [
    "figure_deformee",
    "figure_diagramme",
    "figure_efforts",
    "figure_geometrie",
    "figure_moment_courbure",
]
