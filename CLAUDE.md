# Feuille-de-calcul

Outils de calcul d'ingénieur civil (bureau IngPhi SA), en Python, selon les normes SIA.
Langue du projet : **français** (code, commentaires, commits, documentation).

## Contenu du dépôt

| Dossier | Rôle |
|---|---|
| `Mur contre terre/` | Application principale : vérification d'un mur de sous-sol en béton armé (SIA 260/261/262/267). Voir son `README.md` et `docs/plan-conception.html`. |
| `Retrait et armature minimale/` | Futur outil ; contient seulement les feuilles Excel source pour l'instant. |
| `.claude/skills/` | Skills de projet : `verification-normative`, `tests-reference`, `rapport-calcul`, `release-pyinstaller`. |

## Règle impérative : droit d'auteur des normes

Les normes SIA sont protégées. **Ne jamais lire, afficher ni extraire le texte** des normes PDF/Markdown
(`normes_pdf/`, `normes_md/`, dépôt Normes_SIA_Artifact), ni les committer. L'utilisateur les exploite lui-même avec le script
et un LLM local.
- Seule exception : `261-C1_2023_f.pdf` (rectificatif de 3 pages), autorisé comme fichier de test.
- Pour déboguer, se limiter aux métadonnées (taille, nombre de pages, rotation des pages, polices)
  ou demander à l'utilisateur de vérifier lui-même le rendu.

## Mur contre terre — état

Paquet `mur-contre-terre` v0.3.0, Python ≥ 3.11, `numpy` seul obligatoire. Lots 1 à 11 terminés
(données, poussée des terres, EF, combinaisons, flexion composée, non-linéaire, note de calcul,
interface, export PDF/Excel, exécutable Windows + CI). **Reste : lot 12**, validation contre les cas
de référence Excel du bureau (skill `tests-reference`).

```bash
cd "Mur contre terre" && python -m venv .venv && .venv\Scripts\Activate.ps1
pip install -e ".[dev]" && python -m pytest
```

Flux git : branches `claude/...` fusionnées dans `main` par pull request.

## Conversion des normes

Déplacée dans le dépôt [Normes_SIA_Artifact](https://github.com/damthon/Normes_SIA_Artifact)
(script `outils/convertir_normes.py`, état du travail, découpage par article).
