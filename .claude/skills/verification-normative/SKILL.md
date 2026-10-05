---
name: verification-normative
description: Contrôle la conformité normative (SIA 260/261/262/267, repli Eurocodes EN 1990/1992-1-1/1997-1) du code de calcul de Mur contre terre. À utiliser quand on modifie ou relit combinaisons, poussée des terres, flexion composée, effort tranchant, lois de matériaux ou coefficients partiels.
---

# Vérification normative — Mur contre terre

Norme de référence : **SIA d'abord**, Eurocode en repli (SIA 262 est harmonisée EN 1992-1-1 ; les valeurs nationales suisses priment). Ne jamais citer un article de mémoire comme certain : si le texte exact n'est pas dans le dépôt ou fourni par l'utilisateur, le dire et marquer `# à recouper (lot 12)` comme le fait déjà le code.

## Table de correspondance code ↔ norme

| Fichier (`src/mur_contre_terre/`) | Sujet | SIA | Repli Eurocode |
|---|---|---|---|
| `mecanique/combinaisons.py` | γG=1,35, γQ=1,5, ψ0/ψ1/ψ2, ELU type 2, ELS fréquent | 260 §4.4.3, tab. 3 | EN 1990 §6.4 |
| `geotechnique/poussee.py` | Coulomb, δk, K0, e_ah,min = 5 kPa si c′>0, β ≤ φ | 261 §4.3.2 | EN 1997-1 annexe C |
| `geotechnique/compactage.py`, `surcharges.py`, `hydrostatique.py` | compactage, surcharges, eau | 261 / 267 (clause à confirmer) | EN 1997-1 |
| `section_ba/modele_beton.py` | parabole-rectangle, γc=1,5, εcu=3,5 ‰ | 262 §4.1, tab. 25 | EN 1992-1-1 §3.1.7, tab. 2.1N |
| `section_ba/modele_acier.py` | bilinéaire à écrouissage, γs=1,15, k≥1,08, εud=45 ‰ (B500B) | 262 §4.1, fig. 11, tab. 26 | EN 1992-1-1 §3.2.7, annexe C |
| `section_ba/flexion_composee.py` | équilibre de section, armature minimale | 262 §4.1, §5 | EN 1992-1-1 §9.2.1.1 |
| `section_ba/effort_tranchant.py` | VRd,c sans étriers | 262 §4.3.3 (τcd, kd) | EN 1992-1-1 §6.2.2 (**actuellement la formule EN**) |
| `donnees/materiaux.py` | classes C…/…, fck/fctm/Ecm, B500B | 262 tab. 4 | EN 1992-1-1 tab. 3.1 |

## Procédure

1. Identifier les fichiers touchés (`git diff`) et les lignes du tableau concernées.
2. Pour chaque constante ou formule modifiée : relire le docstring (clause citée), vérifier que **la constante, l'unité (Pa, N/m³, rad) et la clause citée sont cohérentes** ; les unités SI de base sont imposées par `unites.py`.
3. Points de contrôle récurrents :
   - signes (traction positive dans `modele_beton`/`modele_acier`, compression positive pour N de la section — ne pas mélanger) ;
   - le poids déjaugé sous nappe, et l'absence de double comptage eau/sol ;
   - une combinaison par action variable dominante, ψ0 appliqué aux autres ;
   - γ appliqués une seule fois (charges **ou** résistances, pas les deux) ;
   - dispositifs de ductilité : εs ≤ εud, plateau béton tronqué à εcu.
4. Écarts connus à ne pas « corriger » sans source : l'effort tranchant utilise la formule EN, pas τcd/kd SIA ; compactage SIA 267 non sourcé. Les signaler, ne pas les réécrire de mémoire.
5. Rendre un tableau : élément | clause | conforme / à recouper / écart | action. Toute valeur changée doit citer sa clause dans le docstring et être couverte par un test (voir skill `tests-reference`).
