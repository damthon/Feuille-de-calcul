"""Note de calcul — rapport Markdown traçable, à partir d'un ``Projet`` et de son ``ResultatCalcul``.

Chaque grandeur affichée cite sa clause normative quand elle en a une,
conformément à la traçabilité normative visée par le plan de conception
(§2). Ce module met en forme des résultats déjà calculés (``calcul.py``)
— il ne recalcule rien. L'export PDF (lot 10) convertira ce texte
Markdown ; l'export Excel (lot 10 également) réutilisera les mêmes
données via ``ResultatCalcul`` plutôt que ce texte.
"""

from __future__ import annotations

from mur_contre_terre.calcul import ResultatCalcul
from mur_contre_terre.donnees.projet import Projet
from mur_contre_terre.donnees.sol import TypePoussee
from mur_contre_terre.unites import en_deg, en_kN, en_kN_m2, en_kN_m3, en_MPa


def _table(entetes: list[str], lignes: list[list[str]]) -> str:
    sep = ["---"] * len(entetes)
    corps = "\n".join("| " + " | ".join(ligne) + " |" for ligne in lignes)
    return "| " + " | ".join(entetes) + " |\n| " + " | ".join(sep) + " |\n" + corps


def _section_geometrie(projet: Projet) -> str:
    g = projet.geometrie
    return (
        "## Géométrie\n\n"
        + _table(
            ["Grandeur", "Valeur"],
            [
                ["Hauteur H", f"{g.hauteur:.2f} m"],
                ["Épaisseur en pied", f"{g.ep_base:.3f} m"],
                ["Épaisseur en tête", f"{g.ep_couronnement:.3f} m"],
                ["Débord de semelle (côté intérieur)", f"{g.debord_semelle:.2f} m"],
                ["Épaisseur de semelle", f"{g.ep_semelle:.2f} m"],
                ["Largeur totale de semelle B", f"{g.largeur_semelle:.2f} m"],
            ],
        )
    )


def _section_sol(projet: Projet) -> str:
    s = projet.sol
    type_poussee = "active" if s.type_poussee is TypePoussee.ACTIF else "au repos"
    lignes = [
        ["Poids volumique γ", f"{en_kN_m3(s.gamma):.1f} kN/m³"],
        ["Angle de frottement φ′", f"{en_deg(s.phi):.1f} °"],
        ["Cohésion c′", f"{en_kN_m2(s.c):.1f} kN/m²"],
        ["Type de poussée", f"{type_poussee} (SIA 261 §4.3.2)"],
    ]
    if s.delta is not None:
        lignes.append(["Frottement mur-sol δ", f"{en_deg(s.delta):.1f} °"])
    if s.niveau_nappe is not None:
        lignes.append(["Niveau de nappe (depuis le pied)", f"{s.niveau_nappe:.2f} m"])
    return "## Sol et poussée des terres\n\n" + _table(["Grandeur", "Valeur"], lignes)


def _section_materiaux(projet: Projet) -> str:
    m = projet.materiaux
    lignes = [
        ["Béton", f"fck = {en_MPa(m.beton.fck):.0f} MPa, fctm = {en_MPa(m.beton.fctm):.1f} MPa (SIA 262 §4.1)"],
        ["Acier", f"B500B, fsk = {en_MPa(m.acier.fsk):.0f} MPa (SIA 262 §4.1)"],
        ["Enrobage côté terre", f"{m.enrobage_terre * 1000:.0f} mm"],
        ["Enrobage côté intérieur", f"{m.enrobage_interieur * 1000:.0f} mm"],
    ]
    return "## Matériaux\n\n" + _table(["Grandeur", "Valeur"], lignes)


def _section_combinaisons(resultat: ResultatCalcul) -> str:
    lignes = []
    for combinaison in resultat.combinaisons_elu:
        facteurs = ", ".join(f"{nom} × {f:.2f}" for nom, f in combinaison.facteurs.items())
        lignes.append([combinaison.nom, facteurs])
    return (
        "## Combinaisons ELU (SIA 260 §4.4.3.2)\n\n"
        + _table(["Combinaison", "Facteurs"], lignes)
        + f"\n\n{len(resultat.combinaisons_els)} combinaison(s) ELS générée(s) (SIA 260 §4.4.3.4, non détaillées ici)."
    )


def _section_verifications(resultat: ResultatCalcul) -> str:
    lignes = []
    for v in resultat.verifications:
        lignes.append(
            [
                f"{v.position:.2f}",
                f"{v.epaisseur * 100:.1f}",
                f"{v.armature_terre * 1e4:.2f}",
                f"{v.armature_interieur * 1e4:.2f}",
                f"{en_kN(v.effort_tranchant_ed):.1f}",
                f"{en_kN(v.effort_tranchant_rd):.1f}",
                "OK" if v.verdict_tranchant else "**insuffisant**",
            ]
        )
    avertissement = (
        "\n\n> Résistance à l'effort tranchant (SIA 262 §4.3.3) : formule harmonisée "
        "EN 1992-1-1 §6.2.2, faute d'extrait SIA 262 vérifié pour ce lot — à confirmer "
        "avant toute justification de projet (voir `section_ba/effort_tranchant.py`)."
    )
    return (
        "## Vérification de section — armature nécessaire et effort tranchant (SIA 262 §4.1, §4.3.3)\n\n"
        + _table(
            ["z [m]", "h [cm]", "As terre [cm²/m]", "As intérieur [cm²/m]", "V_Ed [kN]", "V_Rd [kN]", "Effort tranchant"],
            lignes,
        )
        + avertissement
    )


def generer_note_calcul(projet: Projet, resultat: ResultatCalcul) -> str:
    """Note de calcul Markdown : géométrie, sol, matériaux, combinaisons, vérification de section."""
    parties = [
        f"# Note de calcul — {projet.nom}",
        "\nMur de sous-sol contre-terre — vérification SIA 260/261/262. "
        "Généré automatiquement par `mur_contre_terre.rapport` ; ne remplace pas "
        "l'examen critique de l'ingénieur.",
        _section_geometrie(projet),
        _section_sol(projet),
        _section_materiaux(projet),
        _section_combinaisons(resultat),
        _section_verifications(resultat),
    ]
    return "\n\n".join(parties) + "\n"
