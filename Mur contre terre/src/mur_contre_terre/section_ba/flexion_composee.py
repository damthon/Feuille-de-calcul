"""Flexion composée N+M — équilibre de section, armature nécessaire.

Section rectangulaire (largeur ``b``, épaisseur ``h`` — tranche de mur de
1,00 m par défaut, comme le reste du paquet) portant deux lits
d'armature, un par face. Repère local ``z`` propre à ce module,
indépendant du repère global du maillage (comme ``geotechnique.poussee``
pour la profondeur) : ``z = 0`` à la face côté terre, ``z = h`` à la face
côté intérieur, ``z`` croissant de la face terre vers la face intérieure.
Le centre de gravité de la section brute est à ``z = h/2``.

Convention de signe — à respecter par l'appelant lorsqu'il traduira les
efforts enveloppe du maillage (lot 3/4, hors périmètre de ce lot) vers
cette section : ``N_Ed`` est positif en traction (même convention que
``mecanique.solveur_lineaire.ResultatMecanique.effort_normal``) ;
``M_Ed`` est le moment autour du centre de gravité tel qu'un moment
positif tend la fibre ``z = h`` (face intérieure). L'appelant indique
explicitement, via ``face_tendue``, quelle face est tendue sous le
couple (N_Ed, M_Ed) considéré — ce module ne fait pas ce choix : il
vérifie/dimensionne une face à la fois, comme le veut une vérification
par combinaison (chaque combinaison peut tendre une face différente).

Équilibre de section : compatibilité des déformations (Navier-Bernoulli,
sections planes), profil linéaire ``ε(s) = εcu·(s/x − 1)`` où ``s`` est la
distance à la fibre extrême comprimée et ``x`` la profondeur de l'axe
neutre depuis cette fibre — c'est-à-dire la fibre extrême comprimée fixée
à son état ultime (−εcu, écrasement du béton, SIA 262 §4.1). C'est le
domaine courant pour une paroi normalement armée (voir la note d'erreur
de ``armature_necessaire`` si ce domaine n'est pas atteignable). Le
béton est intégré numériquement (règle des trapèzes, ``N_FIBRES``
intervalles) ; les lits d'armature sont des contributions ponctuelles.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from mur_contre_terre.donnees.materiaux import Materiaux
from mur_contre_terre.section_ba.modele_acier import contrainte_acier
from mur_contre_terre.section_ba.modele_beton import contrainte_beton

N_FIBRES = 200  # intervalles d'intégration numérique (trapèzes) sur la hauteur de la section
_SIGMA_T_MIN = 1.0  # Pa — garde-fou contre la singularité numérique axe neutre ≈ lit tendu


@dataclass(frozen=True)
class SectionRectangulaire:
    """Section rectangulaire d'une tranche de mur — largeur b (1,00 m par défaut), épaisseur h.

    ``enrobage_terre``/``enrobage_interieur`` positionnent l'axe de
    chaque lit d'armature depuis la face correspondante (approximation
    au centre de gravité des barres, sans diamètre — cohérent avec
    ``donnees.materiaux.Materiaux``, dont le choix des diamètres réels
    reste hors périmètre de ce lot).
    """

    epaisseur: float  # h [m]
    enrobage_terre: float  # [m], depuis la face z = 0
    enrobage_interieur: float  # [m], depuis la face z = h
    largeur: float = 1.0  # b [m]

    def __post_init__(self) -> None:
        if self.epaisseur <= 0:
            raise ValueError(f"SectionRectangulaire.epaisseur doit être strictement positive (reçu {self.epaisseur})")
        if self.largeur <= 0:
            raise ValueError(f"SectionRectangulaire.largeur doit être strictement positive (reçu {self.largeur})")
        if not 0.0 < self.enrobage_terre < self.epaisseur:
            raise ValueError("SectionRectangulaire.enrobage_terre doit être dans ]0, epaisseur[")
        if not 0.0 < self.enrobage_interieur < self.epaisseur:
            raise ValueError("SectionRectangulaire.enrobage_interieur doit être dans ]0, epaisseur[")
        if self.enrobage_terre + self.enrobage_interieur >= self.epaisseur:
            raise ValueError("La somme des enrobages doit rester inférieure à l'épaisseur")

    @property
    def z_armature_terre(self) -> float:
        """Position (axe) du lit d'armature côté terre, depuis z = 0."""
        return self.enrobage_terre

    @property
    def z_armature_interieur(self) -> float:
        """Position (axe) du lit d'armature côté intérieur, depuis z = 0."""
        return self.epaisseur - self.enrobage_interieur


@dataclass(frozen=True)
class ResultatFlexionComposee:
    """``profondeur_axe_neutre`` et ``deformation_acier_tendu`` ne sont représentatifs de l'état
    limite exact que lorsque ``armature_calculee`` gouverne (> armature_minimale) ; lorsque
    l'armature minimale gouverne, l'équilibre exact (N_Ed, M_Ed) n'est plus atteint avec l'aire
    réellement retenue et ces deux champs ne servent qu'à documenter le calcul intermédiaire."""

    face_tendue: str
    profondeur_axe_neutre: float  # x [m], depuis la fibre extrême comprimée
    armature_calculee: float  # As requis par l'équilibre exact [m²/m], ≥ 0
    armature_minimale: float  # As,min normatif [m²/m]
    armature_necessaire: float  # max(calculée, minimale) — valeur à retenir [m²/m]
    deformation_acier_tendu: float  # ε au lit tendu, pour contrôle de ductilité (< Acier.epsilon_ud)


def _trapezes(valeurs: np.ndarray, z: np.ndarray) -> float:
    """Intégrale ∫ valeurs dz par la règle des trapèzes (équivalent à numpy.trapezoid, sans dépendre
    d'une version précise de numpy — ``trapz`` a été retiré au profit de ``trapezoid`` en numpy 2.0)."""
    return float(np.sum((valeurs[:-1] + valeurs[1:]) * np.diff(z)) / 2.0)


def _position_pour_face(section: SectionRectangulaire, face_tendue: str) -> tuple[int, float, float]:
    """(sens, z_tendue, z_comprimee) — sens = +1 si la fibre extrême comprimée est en z=0."""
    if face_tendue == "interieur":
        return 1, section.z_armature_interieur, section.z_armature_terre
    if face_tendue == "terre":
        return -1, section.z_armature_terre, section.z_armature_interieur
    raise ValueError(f"face_tendue doit être 'terre' ou 'interieur' (reçu {face_tendue!r})")


@dataclass(frozen=True)
class _Composantes:
    z_tendue: float
    z_comprimee: float
    fc: float  # résultante de la contrainte de béton [N]
    mc: float  # moment de la contrainte de béton autour de h/2 [N·m]
    eps_tendue: float
    eps_comprimee: float
    sigma_tendue: float  # contrainte dans l'acier tendu, pour As = 1 [Pa]
    sigma_comprimee: float  # contrainte dans l'acier comprimé, pour As = 1 [Pa]


def _composantes(
    x: float, section: SectionRectangulaire, materiaux: Materiaux, face_tendue: str, calcul: bool
) -> _Composantes:
    """Intégration par fibres du béton et déformations/contraintes des deux lits d'armature, à x donné."""
    if x <= 0.0:
        raise ValueError(f"x doit être strictement positif (reçu {x})")
    sens, z_tendue, z_comprimee = _position_pour_face(section, face_tendue)
    h = section.epaisseur
    eps_cu = materiaux.beton.epsilon_cu

    z = np.linspace(0.0, h, N_FIBRES + 1)
    s = z if sens == 1 else h - z
    eps_beton = eps_cu * (s / x - 1.0)
    sigma_beton = contrainte_beton(eps_beton, materiaux.beton, calcul)
    fc = section.largeur * _trapezes(sigma_beton, z)
    mc = section.largeur * _trapezes(sigma_beton * (z - h / 2.0), z)

    def _deformation(z_lit: float) -> float:
        s_lit = z_lit if sens == 1 else h - z_lit
        return eps_cu * (s_lit / x - 1.0)

    eps_t = _deformation(z_tendue)
    eps_c = _deformation(z_comprimee)
    sigma_t = contrainte_acier(eps_t, materiaux.acier, calcul)
    sigma_c = contrainte_acier(eps_c, materiaux.acier, calcul)

    return _Composantes(z_tendue, z_comprimee, fc, mc, eps_t, eps_c, sigma_t, sigma_c)


def equilibre(
    x: float,
    armature_tendue: float,
    armature_comprimee: float,
    section: SectionRectangulaire,
    materiaux: Materiaux,
    face_tendue: str,
    calcul: bool = True,
) -> tuple[float, float]:
    """(N, M) résultants pour un axe neutre ``x`` et des aires d'armature données.

    ``x`` est la profondeur de l'axe neutre depuis la fibre extrême
    comprimée, fixée à son état ultime −εcu (SIA 262 §4.1). Fonction de
    vérification, indépendante du dimensionnement — ``armature_necessaire``
    l'utilise en interne pour rechercher l'équilibre, mais elle sert aussi
    à vérifier une armature déjà posée.
    """
    if armature_tendue < 0.0 or armature_comprimee < 0.0:
        raise ValueError("les aires d'armature doivent être positives ou nulles")

    c = _composantes(x, section, materiaux, face_tendue, calcul)
    h = section.epaisseur
    n = c.fc + armature_comprimee * c.sigma_comprimee + armature_tendue * c.sigma_tendue
    m = (
        c.mc
        + armature_comprimee * c.sigma_comprimee * (c.z_comprimee - h / 2.0)
        + armature_tendue * c.sigma_tendue * (c.z_tendue - h / 2.0)
    )
    return n, m


def _as_tendue_et_residu(
    x: float,
    n_ed: float,
    m_ed: float,
    section: SectionRectangulaire,
    materiaux: Materiaux,
    face_tendue: str,
    armature_comprimee: float,
) -> tuple[float, float, float] | None:
    """(As requis par l'équilibre en N, résidu de moment, ε au lit tendu) — None si singulier en ``x``."""
    c = _composantes(x, section, materiaux, face_tendue, True)
    if abs(c.sigma_tendue) < _SIGMA_T_MIN:
        return None

    h = section.epaisseur
    as_t = (n_ed - c.fc - armature_comprimee * c.sigma_comprimee) / c.sigma_tendue
    m_pred = (
        c.mc
        + armature_comprimee * c.sigma_comprimee * (c.z_comprimee - h / 2.0)
        + as_t * c.sigma_tendue * (c.z_tendue - h / 2.0)
    )
    return as_t, m_pred - m_ed, c.eps_tendue


def _resoudre_axe_neutre(
    n_ed: float,
    m_ed: float,
    section: SectionRectangulaire,
    materiaux: Materiaux,
    face_tendue: str,
    armature_comprimee: float,
) -> tuple[float, float, float]:
    """(x, As tendue, ε au lit tendu) à l'équilibre exact — bissection sur x."""
    h = section.epaisseur
    bornes = np.linspace(1e-4 * h, 3.0 * h, 400)

    x_bas = r_bas = None
    x_haut = None
    for x in bornes:
        etat = _as_tendue_et_residu(x, n_ed, m_ed, section, materiaux, face_tendue, armature_comprimee)
        if etat is None:
            continue
        r = etat[1]
        if x_bas is None:
            x_bas, r_bas = x, r
            continue
        if r_bas * r <= 0.0:
            x_haut = x
            break
        x_bas, r_bas = x, r

    if x_haut is None:
        raise ValueError(
            "Aucun équilibre trouvé pour ce couple (N_Ed, M_Ed) avec la fibre extrême comprimée à "
            "epsilon_cu (domaine courant d'une paroi normalement armée) — cas hors du domaine couvert "
            "par ce modèle au lot 5 (par exemple compression quasi centrée dominante), ou incohérence "
            "de signe entre M_Ed et face_tendue (M_Ed > 0 tend la face 'interieur', M_Ed < 0 tend la "
            "face 'terre' — voir l'en-tête du module)."
        )

    for _ in range(60):
        x_mid = 0.5 * (x_bas + x_haut)
        etat = _as_tendue_et_residu(x_mid, n_ed, m_ed, section, materiaux, face_tendue, armature_comprimee)
        if etat is None or r_bas * etat[1] > 0.0:
            x_bas, r_bas = x_mid, (etat[1] if etat is not None else r_bas)
        else:
            x_haut = x_mid

    x_final = 0.5 * (x_bas + x_haut)
    etat = _as_tendue_et_residu(x_final, n_ed, m_ed, section, materiaux, face_tendue, armature_comprimee)
    assert etat is not None  # la borne x_haut, par construction, ne l'est pas
    as_t, _, eps_t = etat
    return x_final, as_t, eps_t


def armature_minimale(section: SectionRectangulaire, materiaux: Materiaux, hauteur_utile: float) -> float:
    """As,min = max(0,26·fctm/fsk·b·d ; 0,0013·b·d) [m²/m].

    Harmonisé EN 1992-1-1 §9.2.1.1(1) — à recouper avec le texte exact de
    la SIA 262 au lot 12, comme la résistance à l'effort tranchant
    (voir ``effort_tranchant.py``).
    """
    if hauteur_utile <= 0:
        raise ValueError(f"hauteur_utile doit être strictement positive (reçu {hauteur_utile})")
    b = section.largeur
    fctm, fsk = materiaux.beton.fctm, materiaux.acier.fsk
    return max(0.26 * fctm / fsk * b * hauteur_utile, 0.0013 * b * hauteur_utile)


def armature_necessaire(
    n_ed: float,
    m_ed: float,
    section: SectionRectangulaire,
    materiaux: Materiaux,
    face_tendue: str,
    armature_comprimee: float = 0.0,
) -> ResultatFlexionComposee:
    """Armature nécessaire côté ``face_tendue`` ('terre' ou 'interieur') pour résister (N_Ed, M_Ed).

    ``armature_comprimee`` est l'aire d'armature déjà posée côté opposé
    (donnée, non dimensionnée ici — 0 par défaut si aucune n'est prévue
    à cette face pour cette combinaison).

    Recherche par bissection la profondeur d'axe neutre x telle que
    l'équilibre (``equilibre``) avec la fibre extrême comprimée à −εcu
    redonne exactement (N_Ed, M_Ed) ; l'aire d'armature tendue calculée
    en découle par équilibre des efforts normaux. Un résultat négatif
    (section surabondamment comprimée pour ce couple d'efforts) est
    ramené à 0 — c'est alors ``armature_minimale`` qui gouverne, comme
    prescrit normativement.
    """
    if armature_comprimee < 0.0:
        raise ValueError(f"armature_comprimee doit être positive ou nulle (reçu {armature_comprimee})")
    _position_pour_face(section, face_tendue)  # valide face_tendue, lève sinon

    x, as_calculee, eps_tendue = _resoudre_axe_neutre(n_ed, m_ed, section, materiaux, face_tendue, armature_comprimee)

    h = section.epaisseur
    enrobage_tendu = section.enrobage_interieur if face_tendue == "interieur" else section.enrobage_terre
    hauteur_utile = h - enrobage_tendu
    as_min = armature_minimale(section, materiaux, hauteur_utile)
    as_calculee_positive = max(as_calculee, 0.0)

    # La déformation géométrique brute peut dépasser epsilon_ud pour un moment très faible
    # (axe neutre proche de la fibre comprimée) : la contrainte d'acier utilisée dans
    # l'équilibre est de toute façon plafonnée par modele_acier.contrainte_acier — ce cas
    # correspond en pratique à as_calculee très faible, dominé par armature_minimale.
    eps_tendue_rapportee = math.copysign(min(abs(eps_tendue), materiaux.acier.epsilon_ud), eps_tendue)

    return ResultatFlexionComposee(
        face_tendue=face_tendue,
        profondeur_axe_neutre=x,
        armature_calculee=as_calculee_positive,
        armature_minimale=as_min,
        armature_necessaire=max(as_calculee_positive, as_min),
        deformation_acier_tendu=eps_tendue_rapportee,
    )
