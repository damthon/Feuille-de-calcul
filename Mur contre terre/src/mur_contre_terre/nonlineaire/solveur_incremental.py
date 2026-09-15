"""Solveur incrémental non linéaire — charge par paliers, EI(x) mis à jour (§9 du plan de conception).

Orchestration : contrairement aux modules ``mecanique/`` et
``section_ba/`` (qui s'ignorent mutuellement, voir leurs en-têtes
respectifs), ce module appelle les deux — c'est le rôle attendu d'une
couche d'orchestration en aval, cohérent avec le flux de calcul §5 du
plan de conception.

La charge (vecteur de forces nodales à 100 %) est appliquée par paliers
successifs (``fractions_charge`` — même liste que ``donnees.Projet.pas_de_charge``,
lot 1 : « 1 %, …, 100 %, pas paramétrable » du plan de conception). À
chaque palier : le maillage est résolu élastiquement (rigidité axiale EA
constante, section brute — seule EI est mise à jour, comme le prescrit
§9 du plan) ; pour chaque élément,
les efforts internes (N, M — moyenne des deux extrémités pour M, qui y
varie linéairement) déterminent une nouvelle rigidité sécante EI via
``section_ba.moment_courbure.rigidite_secante`` ; on itère (relaxation
par moyenne, pour la stabilité) jusqu'à ce que l'écart relatif entre
deux EI successifs passe sous ``tolerance``, ou jusqu'à
``max_iterations`` sans convergence. Le premier palier qui ne converge
pas (ou dont une section dépasse sa résistance) arrête le chargement :
le dernier palier convergé est la charge maximale atteinte sous cette
hypothèse d'armature.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from mur_contre_terre.donnees.appuis import ConditionsAppui
from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.donnees.materiaux import Materiaux
from mur_contre_terre.donnees.sol import Sol
from mur_contre_terre.mecanique.maillage import Maillage
from mur_contre_terre.mecanique.rigidite import rigidites_par_element
from mur_contre_terre.mecanique.solveur_lineaire import ResultatMecanique, resoudre
from mur_contre_terre.section_ba.flexion_composee import SectionRectangulaire
from mur_contre_terre.section_ba.moment_courbure import rigidite_non_fissuree, rigidite_secante

MOMENT_NEGLIGEABLE = 1.0  # N·m — sous ce seuil, EI reste à la valeur non fissurée (évite une bissection inutile)


@dataclass(frozen=True)
class PalierIncremental:
    fraction_charge: float  # 0 < f <= 1
    resultat: ResultatMecanique
    ei: tuple[float, ...]  # EI sécant convergé par élément [N·m²]
    nb_iterations: int


@dataclass(frozen=True)
class ResultatIncremental:
    paliers: tuple[PalierIncremental, ...]  # paliers convergés, charge croissante
    convergence_totale: bool  # True si tous les paliers demandés ont convergé
    fraction_charge_maximale: float  # dernier palier convergé (0.0 si aucun)


def _fractions_charge_defaut() -> tuple[float, ...]:
    return tuple(i / 20 for i in range(1, 21))  # 5 %, 10 %, …, 100 % — même défaut que Projet.pas_de_charge


def _sections(geometrie: Geometrie, materiaux: Materiaux, maillage: Maillage) -> tuple[SectionRectangulaire, ...]:
    return tuple(
        SectionRectangulaire(
            epaisseur=geometrie.epaisseur(maillage.milieu_element(i)),
            enrobage_terre=materiaux.enrobage_terre,
            enrobage_interieur=materiaux.enrobage_interieur,
        )
        for i in range(maillage.nb_elements)
    )


def _armatures_par_element(armature: Sequence[float] | float, nb_elements: int, nom: str) -> tuple[float, ...]:
    if isinstance(armature, (int, float)):
        return (float(armature),) * nb_elements
    valeurs = tuple(armature)
    if len(valeurs) != nb_elements:
        raise ValueError(f"{nom} doit avoir une valeur par élément du maillage ({nb_elements}), reçu {len(valeurs)}")
    return valeurs


def _ei_element(
    m_repr: float,
    n_repr: float,
    section: SectionRectangulaire,
    materiaux: Materiaux,
    armature_terre: float,
    armature_interieur: float,
) -> float:
    if abs(m_repr) < MOMENT_NEGLIGEABLE:
        return rigidite_non_fissuree(section, materiaux)
    return rigidite_secante(m_repr, n_repr, section, materiaux, armature_terre, armature_interieur)


def resoudre_incremental(
    maillage: Maillage,
    geometrie: Geometrie,
    materiaux: Materiaux,
    appuis: ConditionsAppui,
    sol: Sol,
    forces_nodales: np.ndarray,
    armature_terre: Sequence[float] | float,
    armature_interieur: Sequence[float] | float,
    fractions_charge: Sequence[float] = (),
    tolerance: float = 1e-3,
    max_iterations: int = 30,
) -> ResultatIncremental:
    """Charge ``forces_nodales`` (à 100 %) par paliers, EI(x) mis à jour à convergence à chaque palier.

    ``armature_terre``/``armature_interieur`` : aire d'armature [m²/m]
    par élément (scalaire si constante sur toute la hauteur, ou une
    valeur par élément du maillage). L'armature elle-même n'est pas
    dimensionnée ici — c'est ``section_ba.flexion_composee`` qui le
    fait, à un stade antérieur du calcul. ``fractions_charge`` (défaut :
    5 %, 10 %, …, 100 %) n'a pas besoin d'être uniforme ni triée — elle
    est parcourue dans l'ordre donné, comme ``Projet.pas_de_charge``.
    """
    fractions_charge = tuple(fractions_charge) or _fractions_charge_defaut()
    if any(not 0.0 < f <= 1.0 for f in fractions_charge):
        raise ValueError("fractions_charge doit contenir des fractions dans ]0, 1]")
    if not 0.0 < tolerance < 1.0:
        raise ValueError(f"tolerance doit être dans ]0, 1[ (reçu {tolerance})")
    if max_iterations < 1:
        raise ValueError(f"max_iterations doit être strictement positif (reçu {max_iterations})")

    forces_nodales = np.asarray(forces_nodales, dtype=float)
    if forces_nodales.shape != (maillage.nb_dof,):
        raise ValueError(f"forces_nodales doit avoir {maillage.nb_dof} valeurs (reçu {forces_nodales.shape})")

    n_el = maillage.nb_elements
    sections = _sections(geometrie, materiaux, maillage)
    as_terre = _armatures_par_element(armature_terre, n_el, "armature_terre")
    as_interieur = _armatures_par_element(armature_interieur, n_el, "armature_interieur")

    ea, ei_non_fissure = rigidites_par_element(geometrie, materiaux, maillage)

    ei_convergee = list(ei_non_fissure)
    paliers: list[PalierIncremental] = []

    for fraction in fractions_charge:
        f_palier = fraction * forces_nodales
        ei_iter = list(ei_convergee)

        resultat: ResultatMecanique | None = None
        convergee = False
        iterations_faites = 0
        for iteration in range(1, max_iterations + 1):
            iterations_faites = iteration
            resultat = resoudre(maillage, ea, ei_iter, appuis, sol, geometrie, f_palier)

            ei_nouveau: list[float] = []
            echec = False
            for i in range(n_el):
                m_repr = 0.5 * (resultat.moment_flechissant[i, 0] + resultat.moment_flechissant[i, 1])
                n_repr = resultat.effort_normal[i, 0]
                try:
                    ei_nouveau.append(_ei_element(m_repr, n_repr, sections[i], materiaux, as_terre[i], as_interieur[i]))
                except ValueError:
                    echec = True
                    break
            if echec:
                break

            ecart = max(abs(a - b) / b for a, b in zip(ei_nouveau, ei_iter))
            if ecart < tolerance:
                ei_iter = ei_nouveau
                convergee = True
                break
            ei_iter = [0.5 * (a + b) for a, b in zip(ei_nouveau, ei_iter)]

        if not convergee:
            break

        assert resultat is not None
        paliers.append(PalierIncremental(fraction, resultat, tuple(ei_iter), iterations_faites))
        ei_convergee = ei_iter

    convergence_totale = len(paliers) == len(fractions_charge)
    fraction_max = paliers[-1].fraction_charge if paliers else 0.0
    return ResultatIncremental(tuple(paliers), convergence_totale, fraction_max)
