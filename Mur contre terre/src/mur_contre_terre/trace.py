"""Figures — géométrie, charges, diagrammes N/V/M, moment-courbure, déformée (extra ``[trace]``, matplotlib).

Chaque fonction construit et retourne une ``matplotlib.figure.Figure``
sans l'afficher ni l'enregistrer — à l'appelant (CLI, interface de
bureau, export du rapport) de faire ``figure.savefig(...)`` ou de
l'intégrer à un canevas Tkinter (``FigureCanvasTkAgg``). Ce module
n'est importable que si l'extra ``matplotlib`` est installé
(``pip install -e ".[trace]"``) — dépendance volontairement non
obligatoire à l'exécution, comme le veut le plan de conception (§3).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from mur_contre_terre.donnees.appuis import ConditionsAppui, TypeAppuiPied, TypeAppuiTete
from mur_contre_terre.donnees.charges import CasDeCharge, CategorieAction, TypeCharge
from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.donnees.materiaux import Materiaux
from mur_contre_terre.donnees.sol import Sol
from mur_contre_terre.mecanique.maillage import Maillage
from mur_contre_terre.mecanique.solveur_lineaire import ResultatMecanique
from mur_contre_terre.section_ba.moment_courbure import PointMomentCourbure
from mur_contre_terre.unites import en_kN, en_kN_m2, en_kNm, en_MPa

_COULEUR_MUR = "#ECE8DF"
_COULEUR_TERRE = "#DDD2B8"
_COULEUR_NAPPE = "#1F6FB2"
_COULEURS_CATEGORIE = {CategorieAction.G: "#4A4A4A", CategorieAction.Q: "#1F6FB2", CategorieAction.A: "#A8391A"}
_COULEUR_PREVISUALISATION = "#D98A28"


def _dessiner_mur(ax: plt.Axes, geometrie: Geometrie) -> float:
    """Coupe schématique à l'échelle du mur et de sa semelle avant. Retourne l'épaisseur en pied."""
    h = geometrie.hauteur
    z = np.linspace(0.0, h, 50)
    x_interieur = [geometrie.epaisseur(zi) for zi in z]
    contour_x = [0.0] + x_interieur + [0.0]
    contour_z = [0.0] + list(z) + [h]
    ax.fill(contour_x, contour_z, color=_COULEUR_MUR, edgecolor="black", linewidth=1.2, zorder=2)

    b = geometrie.debord_semelle
    x0 = geometrie.epaisseur(0.0)
    semelle_x = [0.0, x0 + b, x0 + b, 0.0]
    semelle_z = [0.0, 0.0, -geometrie.ep_semelle, -geometrie.ep_semelle]
    ax.fill(semelle_x, semelle_z, color=_COULEUR_MUR, edgecolor="black", linewidth=1.2, zorder=2)
    return x0


def _dessiner_terrain(ax: plt.Axes, geometrie: Geometrie, sol: Sol) -> float:
    """Massif de terre retenu (côté terre, x<0), terrain incliné de β et niveau de nappe. Retourne
    l'étendue horizontale dessinée (pour le dimensionnement des autres éléments du schéma)."""
    h = geometrie.hauteur
    profondeur = max(1.0, 0.6 * h)
    z_haut_loin = h + profondeur * math.tan(sol.beta)

    x_sol = [0.0, -profondeur, -profondeur, 0.0]
    z_sol = [h, z_haut_loin, -geometrie.ep_semelle, -geometrie.ep_semelle]
    ax.fill(x_sol, z_sol, color=_COULEUR_TERRE, edgecolor="#8A7A54", linewidth=0.8, hatch="....", zorder=0)
    ax.plot([0.0, -profondeur], [h, z_haut_loin], color="#5B4A2A", linewidth=1.4, zorder=1)

    if sol.niveau_nappe is not None:
        z_nappe = sol.niveau_nappe
        ax.plot([-profondeur, 0.0], [z_nappe, z_nappe], color=_COULEUR_NAPPE, linestyle="--", linewidth=1.3, zorder=3)
        ax.fill(
            [0.0, -profondeur, -profondeur, 0.0],
            [z_nappe, z_nappe, -geometrie.ep_semelle, -geometrie.ep_semelle],
            color="#BFE0F5", alpha=0.5, zorder=1,
        )
        ax.annotate(
            f"Nappe z={z_nappe:.2f} m", xy=(-profondeur * 0.5, z_nappe), xytext=(0, 4),
            textcoords="offset points", fontsize=7, color=_COULEUR_NAPPE, ha="center",
        )
    return profondeur


def _dessiner_appuis(ax: plt.Axes, geometrie: Geometrie, appuis: ConditionsAppui, x0: float) -> None:
    """Symboles d'appui au pied (encastrement/ressort) et en tête (libre/appui dalle)."""
    h = geometrie.hauteur
    b = geometrie.debord_semelle
    y_pied = -geometrie.ep_semelle

    if appuis.pied is TypeAppuiPied.RESSORT:
        xc = (x0 + b) / 2
        xs = [xc + 0.08 * ((-1) ** i) for i in range(7)]
        zs = list(np.linspace(y_pied, y_pied - 0.35, 7))
        ax.plot(xs, zs, color="#1F4E63", linewidth=1.3, zorder=4)
        ax.plot([xc], [y_pied - 0.38], marker="s", markersize=6, color="#1F4E63", zorder=4)
        ax.annotate(
            "kθ (ressort)", xy=(xc, y_pied - 0.38), xytext=(6, -4), textcoords="offset points", fontsize=7
        )
    else:
        ax.plot([-0.1, x0 + b + 0.1], [y_pied, y_pied], color="black", linewidth=1.6, zorder=4)
        for xh in np.linspace(-0.05, x0 + b + 0.05, 10):
            ax.plot([xh, xh - 0.08], [y_pied, y_pied - 0.12], color="black", linewidth=0.8, zorder=4)
        ax.annotate("encastrement", xy=(x0 + b, y_pied), xytext=(4, -12), textcoords="offset points", fontsize=7)

    x_tete = geometrie.epaisseur(h)
    if appuis.tete is TypeAppuiTete.APPUI_DALLE:
        ax.plot([x_tete, x_tete + 0.5], [h, h], color="#1F4E63", linewidth=2.2, zorder=4)
        ax.plot([x_tete + 0.15], [h], marker=">", markersize=8, color="#1F4E63", zorder=4)
        ax.annotate("appui dalle", xy=(x_tete + 0.5, h), xytext=(4, 4), textcoords="offset points", fontsize=7)
    else:
        ax.annotate("tête libre", xy=(x_tete, h), xytext=(4, 4), textcoords="offset points", fontsize=7, color="#777777")


def figure_geometrie(geometrie: Geometrie, sol: Sol | None = None, appuis: ConditionsAppui | None = None) -> Figure:
    """Coupe schématique à l'échelle du mur, avec en option le massif de terre/nappe (``sol``)
    et les symboles d'appui (``appuis``) — sert d'aperçu graphique aux onglets Géométrie, Sol et Appuis."""
    fig, ax = plt.subplots(figsize=(4, 6))
    x0 = _dessiner_mur(ax, geometrie)

    if sol is not None:
        try:
            _dessiner_terrain(ax, geometrie, sol)
        except Exception:
            pass
    if appuis is not None:
        try:
            _dessiner_appuis(ax, geometrie, appuis, x0)
        except Exception:
            pass

    ax.set_xlabel("épaisseur [m]")
    ax.set_ylabel("hauteur z [m]")
    ax.set_title("Géométrie du mur")
    ax.set_aspect("equal", adjustable="box")
    ax.margins(0.12)
    fig.tight_layout()
    return fig


def figure_section_materiaux(geometrie: Geometrie, materiaux: Materiaux) -> Figure:
    """Coupe horizontale schématique en pied de mur : épaisseur, enrobages et classes de matériaux."""
    fig, ax = plt.subplots(figsize=(5, 4.5))
    epaisseur = geometrie.ep_base
    h_coupe = 0.5
    ax.add_patch(Rectangle((0.0, 0.0), epaisseur, h_coupe, facecolor=_COULEUR_MUR, edgecolor="black", linewidth=1.2, zorder=2))

    et, ei = materiaux.enrobage_terre, materiaux.enrobage_interieur
    for y in np.linspace(0.07, h_coupe - 0.07, 5):
        ax.plot(et, y, marker="o", markersize=5, color="#1F4E63", zorder=3)
        ax.plot(epaisseur - ei, y, marker="o", markersize=5, color="#9C5A2E", zorder=3)

    y_cote = -0.08
    ax.annotate("", xy=(et, y_cote), xytext=(0.0, y_cote), arrowprops={"arrowstyle": "<->", "color": "black", "lw": 0.9})
    ax.text(et / 2, y_cote - 0.04, f"{et * 1000:.0f} mm", ha="center", fontsize=7)
    ax.annotate(
        "", xy=(epaisseur, y_cote), xytext=(epaisseur - ei, y_cote),
        arrowprops={"arrowstyle": "<->", "color": "black", "lw": 0.9},
    )
    ax.text(epaisseur - ei / 2, y_cote - 0.04, f"{ei * 1000:.0f} mm", ha="center", fontsize=7)

    # étiquettes de côté en coordonnées d'axes (fraction 0..1) : indépendantes de la déformation
    # d'échelle de l'aspect "equal", donc jamais chevauchées même pour un mur très mince
    ax.text(0.0, 1.03, "◀ côté terre", transform=ax.transAxes, ha="left", va="bottom", fontsize=8, color="#1F4E63")
    ax.text(1.0, 1.03, "côté intérieur ▶", transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color="#9C5A2E")

    ax.set_xlabel("épaisseur [m]")
    ax.set_title(
        f"Section en pied — enrobages\nfck={en_MPa(materiaux.beton.fck):.0f} MPa, fsk={en_MPa(materiaux.acier.fsk):.0f} MPa",
        fontsize=10, pad=22,
    )
    ax.set_aspect("equal", adjustable="box")
    ax.set_yticks([])
    ax.margins(0.25)
    fig.tight_layout()
    return fig


def _fleche(ax: plt.Axes, x1: float, z1: float, x2: float, z2: float, couleur: str, style: str = "-", alpha: float = 1.0) -> None:
    ax.annotate(
        "", xy=(x2, z2), xytext=(x1, z1),
        arrowprops={"arrowstyle": "-|>", "color": couleur, "lw": 1.2, "linestyle": style, "alpha": alpha},
    )


def _dessiner_charge(
    ax: plt.Axes, geometrie: Geometrie, sol: Sol | None, charge: CasDeCharge, couleur: str,
    style: str = "-", alpha: float = 1.0, decalage: float = 0.0,
) -> None:
    """Représentation schématique (position et sens approximatifs, pas les valeurs de calcul exactes)
    d'un cas de charge sur la coupe du mur — voir ``figure_charges``. ``decalage`` étage verticalement
    les charges appliquées au-dessus du mur (tête, surcharges) pour éviter que leurs étiquettes se chevauchent."""
    h = geometrie.hauteur
    p = charge.parametres
    nom = charge.nom or charge.type.value

    if charge.type is TypeCharge.POIDS_PROPRE:
        xc, zc = geometrie.epaisseur(h * 0.5) * 0.5, h * 0.5
        _fleche(ax, xc, zc + 0.35, xc, zc, couleur, style, alpha)
        ax.annotate(nom, xy=(xc, zc), xytext=(5, 0), textcoords="offset points", fontsize=7, color=couleur, alpha=alpha)

    elif charge.type is TypeCharge.CHARGE_TETE:
        xc = geometrie.epaisseur(h) / 2
        y = h + 0.45 + decalage
        _fleche(ax, xc, y, xc, h, couleur, style, alpha)
        ax.annotate(
            f"{nom}\n{en_kN(charge.valeur):.1f} kN", xy=(xc, y), xytext=(5, 2),
            textcoords="offset points", fontsize=7, color=couleur, alpha=alpha,
        )

    elif charge.type is TypeCharge.POUSSEE_TERRES:
        for z in np.linspace(0.08 * h, 0.92 * h, 5):
            longueur = 0.08 + 0.35 * (1 - z / h)
            _fleche(ax, -longueur, z, 0.0, z, couleur, style, alpha)
        ax.annotate(nom, xy=(-0.4, h * 0.5), fontsize=7, color=couleur, ha="right", alpha=alpha)

    elif charge.type in (TypeCharge.SURCHARGE_TETE, TypeCharge.CHARGE_SURFACIQUE_TERREPLEIN):
        distance = p.get("distance", 0.0)
        etendue = p.get("etendue", 1.0)
        y = h + 0.4 + decalage
        xs = np.linspace(-distance - etendue, -distance, 4)
        for x in xs:
            _fleche(ax, x, y, x, h, couleur, style, alpha)
        ax.annotate(
            f"{nom}\n{en_kN_m2(charge.valeur):.1f} kN/m²", xy=(float(np.mean(xs)), y), xytext=(0, 4),
            textcoords="offset points", fontsize=7, color=couleur, ha="center", alpha=alpha,
        )

    elif charge.type is TypeCharge.CHARGE_LINEAIRE_TERREPLEIN:
        distance = p.get("distance", 0.5)
        y = h + 0.4 + decalage
        _fleche(ax, -distance, y, -distance, h, couleur, style, alpha)
        ax.annotate(
            f"{nom}\n{en_kN(charge.valeur):.1f} kN/m", xy=(-distance, y), xytext=(0, 4),
            textcoords="offset points", fontsize=7, color=couleur, ha="center", alpha=alpha,
        )

    elif charge.type is TypeCharge.PRESSION_HYDROSTATIQUE:
        z_nappe = sol.niveau_nappe if (sol is not None and sol.niveau_nappe is not None) else 0.0
        if z_nappe > 0.0:
            for z in np.linspace(0.02, z_nappe * 0.98, 4):
                longueur = 0.06 + 0.3 * (1 - z / z_nappe)
                _fleche(ax, -longueur, z, 0.0, z, couleur, style, alpha)
            ax.annotate(nom, xy=(-0.4, z_nappe * 0.4), fontsize=7, color=couleur, ha="right", alpha=alpha)
        else:
            ax.annotate(f"{nom} (nappe non définie)", xy=(-0.4, h * 0.1), fontsize=7, color=couleur, alpha=alpha)

    elif charge.type is TypeCharge.PRESSION_COMPACTAGE:
        profondeur_app = p.get("profondeur_application", 0.3 * h)
        for z in np.linspace(max(h - profondeur_app, 0.0), h, 4):
            _fleche(ax, -0.28, z, 0.0, z, couleur, style, alpha)
        ax.annotate(
            f"{nom}\n{en_kN_m2(charge.valeur):.1f} kN/m²", xy=(-0.32, h - profondeur_app / 2),
            fontsize=7, color=couleur, ha="right", alpha=alpha,
        )


def figure_charges(
    geometrie: Geometrie,
    sol: Sol | None,
    charges: Sequence[CasDeCharge],
    previsualisation: CasDeCharge | None = None,
) -> Figure:
    """Schéma du mur avec, superposés, tous les cas de charge déjà ajoutés (couleur selon la catégorie
    G/Q/A) et, en pointillés orange, la charge en cours de saisie dans le formulaire (``previsualisation``)."""
    fig, ax = plt.subplots(figsize=(5, 6.5))
    h = geometrie.hauteur
    x0 = _dessiner_mur(ax, geometrie)
    profondeur = 1.3
    if sol is not None:
        try:
            profondeur = _dessiner_terrain(ax, geometrie, sol)
        except Exception:
            pass

    _TYPES_AU_DESSUS = (
        TypeCharge.CHARGE_TETE, TypeCharge.SURCHARGE_TETE,
        TypeCharge.CHARGE_SURFACIQUE_TERREPLEIN, TypeCharge.CHARGE_LINEAIRE_TERREPLEIN,
    )
    decalage = 0.0
    for charge in charges:
        _dessiner_charge(ax, geometrie, sol, charge, _COULEURS_CATEGORIE.get(charge.categorie, "#4A4A4A"), decalage=decalage)
        if charge.type in _TYPES_AU_DESSUS:
            decalage += 0.45
    if previsualisation is not None:
        _dessiner_charge(
            ax, geometrie, sol, previsualisation, _COULEUR_PREVISUALISATION, style="--", alpha=0.85, decalage=decalage
        )
        if previsualisation.type in _TYPES_AU_DESSUS:
            decalage += 0.45

    # limites explicites (les étiquettes de charge au-dessus du mur ne participent pas à l'autoscale
    # matplotlib par défaut — sans cela, les charges les plus hautes seraient rognées hors cadre)
    ax.set_xlim(-profondeur - 0.3, x0 + geometrie.debord_semelle + 0.6)
    ax.set_ylim(-geometrie.ep_semelle - 0.3, h + 0.6 + decalage)

    ax.set_xlabel("épaisseur [m]")
    ax.set_ylabel("hauteur z [m]")
    ax.set_title("Charges appliquées")
    ax.set_aspect("equal", adjustable="box")
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
    "figure_charges",
    "figure_deformee",
    "figure_diagramme",
    "figure_efforts",
    "figure_geometrie",
    "figure_moment_courbure",
    "figure_section_materiaux",
]
