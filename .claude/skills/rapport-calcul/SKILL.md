---
name: rapport-calcul
description: Génère et contrôle la note de calcul de Mur contre terre (Markdown, PDF, Excel) et la cohérence des unités affichées. À utiliser quand on modifie rapport.py, export.py, trace.py ou le format des résultats.
---

# Note de calcul — Mur contre terre

Chaîne : `calcul.calculer(projet)` → `rapport.generer_note_calcul` (Markdown) → `export.py` (PDF via reportlab, Excel via openpyxl) ; figures par `trace.py` (matplotlib). Extras optionnels : `pip install -e ".[export,trace]"`. Les imports lourds sont **locaux** (non au niveau module) — le conserver, sinon le CLI et l'exécutable cassent sans l'extra.

## Contenu attendu d'une note

1. Données : géométrie, sol, appuis, matériaux, charges (avec catégorie d'action et ψ).
2. Hypothèses normatives : SIA 260/261/262/267, γG, γQ, γc, γs, ELU type 2, limites (stabilité d'ensemble non traitée).
3. Actions : poussées (Coulomb, eau, compactage, surcharges) en kN/m² et résultante en kN/m.
4. Combinaisons ELU/ELS retenues et enveloppes M, V, N.
5. Vérifications : MRd/MEd, VRd/VEd, armatures requises vs disposées, déplacements (non linéaire).
6. Conclusion : taux d'utilisation maximal et verdict, avec les avertissements (cas hors domaine, clauses « à recouper »).

## Contrôles d'unités et de forme

- Interne en **SI de base** (Pa, N, m, rad) ; l'affichage convertit : kN, kN/m, kN·m, MPa, mm, cm²/m, degrés. Vérifier chaque ligne convertie une seule fois (pas de 1000× oublié ni doublé).
- Convention de signes expliquée dans la note (traction +, côté terre / côté intérieur).
- Chiffres significatifs : 3 pour les efforts, 1 décimale pour les taux d'utilisation ; jamais d'arrondi avant comparaison au seuil.
- Noms et libellés en français, cohérents entre Markdown, PDF et Excel.

## Procédure

1. `mur-contre-terre verifier <projet.mct> --sortie note.md` puis `.pdf` et `.xlsx` ; les trois doivent donner les mêmes chiffres.
2. `python -m pytest tests/test_rapport.py tests/test_export.py -q`.
3. Ouvrir le PDF/Excel produit et contrôler visuellement (mise en page, figures, accents).
