"""Orchestration bout en bout d'un calcul de mur — assemble tous les modules de calcul (§5 du plan).

Seule couche du dépôt qui connaît à la fois ``mecanique/`` et
``section_ba/`` en dehors de ``nonlineaire/`` (qui l'utilisent tous deux
sans se connaître mutuellement, voir leurs en-têtes respectifs) : c'est
le rôle attendu d'une orchestration en aval. ``interface/`` et
``rapport.py`` n'ont pas de calcul propre — ils appellent ``calculer()``
et affichent/mettent en forme son résultat.

Convention de signe M_Ed → face tendue : le moment fléchissant du
maillage (``mecanique/solveur_lineaire.py`` — ``+u`` pointe du côté
terre vers l'intérieur) coïncide directement avec la convention de
``section_ba/flexion_composee.py`` (M > 0 tend la face intérieure).
Vérifié sur le cas physique de la seule poussée des terres (pousse le
mur vers l'intérieur) : le modèle donne M < 0 au pied et un déplacement
en tête vers l'intérieur — la face terre est donc tendue au pied, ce qui
correspond au comportement normal d'un mur de soutènement (ferraillage
principal côté terre en pied) et à M < 0 ⇒ face terre dans
``flexion_composee``. Aucune conversion de signe n'est donc nécessaire
entre les deux modules (voir ``tests/test_calcul.py``).
"""

from __future__ import annotations

from dataclasses import dataclass

from mur_contre_terre.donnees.materiaux import Materiaux
from mur_contre_terre.donnees.projet import Projet
from mur_contre_terre.mecanique.charges_nodales import vecteur_charge
from mur_contre_terre.mecanique.combinaisons import (
    Combinaison,
    generer_combinaisons_elu,
    generer_combinaisons_els,
    vecteur_combine,
)
from mur_contre_terre.mecanique.maillage import Maillage, generer_maillage
from mur_contre_terre.mecanique.rigidite import rigidites_par_element
from mur_contre_terre.mecanique.solveur_lineaire import ResultatMecanique, resoudre
from mur_contre_terre.section_ba.effort_tranchant import resistance_effort_tranchant, taux_armature_longitudinale
from mur_contre_terre.section_ba.flexion_composee import SectionRectangulaire, armature_minimale, armature_necessaire


@dataclass(frozen=True)
class VerificationSection:
    """Armature nécessaire et vérification de l'effort tranchant à une section (milieu d'élément)."""

    position: float  # z [m], milieu de l'élément
    epaisseur: float  # h [m]
    armature_terre: float  # [m²/m] retenue (max sur les combinaisons ELU, ou armature minimale)
    armature_interieur: float  # [m²/m]
    effort_tranchant_ed: float  # [N], max(|V|) sur les combinaisons ELU
    effort_tranchant_rd: float  # [N], résistance sans armature transversale (voir docstring de calculer())
    verdict_tranchant: bool  # True si effort_tranchant_ed <= effort_tranchant_rd


@dataclass(frozen=True)
class ResultatCalcul:
    maillage: Maillage
    combinaisons_elu: tuple[Combinaison, ...]
    combinaisons_els: tuple[Combinaison, ...]
    resultats_elu: tuple[ResultatMecanique, ...]  # même ordre que combinaisons_elu
    resultats_els: tuple[ResultatMecanique, ...]  # même ordre que combinaisons_els
    verifications: tuple[VerificationSection, ...]  # une par élément du maillage


def _section_element(i: int, geometrie, materiaux: Materiaux, maillage: Maillage) -> SectionRectangulaire:
    return SectionRectangulaire(
        epaisseur=geometrie.epaisseur(maillage.milieu_element(i)),
        enrobage_terre=materiaux.enrobage_terre,
        enrobage_interieur=materiaux.enrobage_interieur,
    )


def verifier_section(
    i: int, geometrie, materiaux: Materiaux, maillage: Maillage, resultats_elu: tuple[ResultatMecanique, ...]
) -> VerificationSection:
    """Armature nécessaire (deux faces) et vérification de l'effort tranchant, enveloppe des combinaisons ELU.

    Pour chaque combinaison, N et M (moyenne des deux extrémités de
    l'élément, M y variant linéairement) déterminent la face tendue et
    l'armature nécessaire (``flexion_composee.armature_necessaire``) ;
    la plus grande valeur retenue par face, sur toutes les combinaisons,
    gouverne — complétée par l'armature minimale normative si aucune
    combinaison ne la dépasse déjà. Une combinaison hors du domaine
    couvert par le modèle actuel (voir l'avertissement de
    ``armature_necessaire``) est ignorée pour le dimensionnement en
    flexion, mais reste prise en compte pour l'effort tranchant.

    Effort tranchant : le taux d'armature utilisé dans
    ``resistance_effort_tranchant`` est celui, conservateur, du lit le
    moins armé des deux faces (la formule EC2 suppose l'armature tendue
    ancrée côté sollicité, qui varie d'une combinaison à l'autre — un
    calcul rigoureux combinaison par combinaison est laissé à un lot
    ultérieur).
    """
    section = _section_element(i, geometrie, materiaux, maillage)
    h = section.epaisseur

    as_terre = 0.0
    as_interieur = 0.0
    for resultat in resultats_elu:
        n = float(resultat.effort_normal[i, 0])
        m = 0.5 * float(resultat.moment_flechissant[i, 0] + resultat.moment_flechissant[i, 1])
        face = "interieur" if m >= 0.0 else "terre"
        try:
            verif = armature_necessaire(n, m, section, materiaux, face)
        except ValueError:
            continue
        if face == "interieur":
            as_interieur = max(as_interieur, verif.armature_necessaire)
        else:
            as_terre = max(as_terre, verif.armature_necessaire)

    d_terre = h - materiaux.enrobage_terre
    d_interieur = h - materiaux.enrobage_interieur
    as_terre = max(as_terre, armature_minimale(section, materiaux, d_terre))
    as_interieur = max(as_interieur, armature_minimale(section, materiaux, d_interieur))

    v_ed = max(abs(float(resultat.effort_tranchant[i, 0])) for resultat in resultats_elu)
    d_min = min(d_terre, d_interieur)
    rho = taux_armature_longitudinale(min(as_terre, as_interieur), section.largeur, d_min)
    v_rd = resistance_effort_tranchant(materiaux.beton, section.largeur, d_min, rho)

    return VerificationSection(
        position=maillage.milieu_element(i),
        epaisseur=h,
        armature_terre=as_terre,
        armature_interieur=as_interieur,
        effort_tranchant_ed=v_ed,
        effort_tranchant_rd=v_rd,
        verdict_tranchant=v_ed <= v_rd,
    )


def calculer(projet: Projet) -> ResultatCalcul:
    """Calcul complet : maillage → charges → combinaisons SIA 260 → solveur linéaire → vérification de section.

    Ne couvre pas la non-linéarité matérielle (``nonlineaire.resoudre_incremental``,
    à appeler séparément avec l'armature retenue ici) ni la validation
    contre les cas de référence (lot 12).
    """
    maillage = generer_maillage(projet.geometrie, projet.finesse_maillage)
    ea, ei = rigidites_par_element(projet.geometrie, projet.materiaux, maillage)

    vecteurs = {
        c.nom: vecteur_charge(c, projet.sol, projet.geometrie, projet.materiaux, maillage) for c in projet.charges
    }
    combinaisons_elu = generer_combinaisons_elu(projet.charges)
    combinaisons_els = generer_combinaisons_els(projet.charges)

    resultats_elu = tuple(
        resoudre(maillage, ea, ei, projet.appuis, projet.sol, projet.geometrie, vecteur_combine(c, vecteurs))
        for c in combinaisons_elu
    )
    resultats_els = tuple(
        resoudre(maillage, ea, ei, projet.appuis, projet.sol, projet.geometrie, vecteur_combine(c, vecteurs))
        for c in combinaisons_els
    )

    verifications = tuple(
        verifier_section(i, projet.geometrie, projet.materiaux, maillage, resultats_elu)
        for i in range(maillage.nb_elements)
    )

    return ResultatCalcul(maillage, combinaisons_elu, combinaisons_els, resultats_elu, resultats_els, verifications)
