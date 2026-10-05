---
name: tests-reference
description: Écrit et maintient les tests de non-régression et cas de référence (calculs à la main, cas Excel du bureau — lot 12) de Mur contre terre. À utiliser pour ajouter un test de calcul, valider une modification de formule ou préparer le lot 12.
---

# Tests de référence — Mur contre terre

Lancer depuis `Mur contre terre/` : `python -m pytest -q` (inclut `--doctest-modules` sur `src/`). Un test par module existe déjà dans `tests/test_<module>.py` : ajouter au fichier correspondant.

## Règles

- **Valeur attendue calculée à la main (ou issue du cas Excel du bureau), jamais en rappelant la fonction testée.** Écrire le détail du calcul en commentaire (formule, unités, source : SIA 26x §… ou fichier Excel + cellule).
- Unités SI via `unites.py` (`kN`, `MPa`, `deg`, `kN_m3`) ; tolérance explicite `pytest.approx(x, rel=1e-3)` — resserrer à 1e-6 seulement pour les formules fermées.
- Cas simples d'abord, ils ont une solution fermée :
  - poussée active Coulomb, mur lisse vertical, φ=30° → Ka = 1/3, e = Ka·γ·z ;
  - poussée hydrostatique triangulaire γw·z ;
  - console encastrée sous charge triangulaire (M = q·h²/6… à recalculer selon le cas) pour le maillage poutre ;
  - section rectangulaire : MRd ≈ As·fsd·z, avec z ≈ 0,9·d comme borne de plausibilité ;
  - effort tranchant sans étriers : VRd,c avec k = 1+√(200/d) ≤ 2.
- Tests de propriété utiles : équilibre (somme des réactions = charges), symétrie, monotonie (plus de charge ⇒ plus de moment), et linéaire ≈ non-linéaire à faible charge.
- Pour les cas bureau (lot 12) : stocker le projet en `.mct` dans `tests/data/`, les résultats Excel attendus en JSON ou constantes commentées avec leur provenance, et comparer via `calculer(projet)`. Écart toléré à documenter (ex. 1 % sur M, 2 % sur As) et justifié par la méthode (EF vs formule simplifiée).
- Un test qui échoue après changement de norme/coefficient : ne pas ajuster la valeur attendue pour « passer » ; remonter l'écart et sa cause.

## Procédure

1. `python -m pytest -q` avant modification (base verte).
2. Écrire le test d'abord avec sa valeur de référence documentée, le voir échouer, corriger le code.
3. Relancer toute la suite, annoncer le nombre de tests et les écarts éventuels.
