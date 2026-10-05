---
name: release-pyinstaller
description: Checklist de version et de publication de l'exécutable Windows MurContreTerre (PyInstaller + GitHub Actions). À utiliser pour préparer une release, changer la version ou diagnostiquer un échec de build.
---

# Release — Mur contre terre

Pipeline : `.github/workflows/build-release.yml`, déclenché par un tag `mur-contre-terre-v*` (ou manuellement avec `version`). Sur runner Windows : `pip install -e ".[dev]"` → `pytest` → `pyinstaller mur_contre_terre.spec` → `dist\MurContreTerre.exe --autotest` → zip → release GitHub.

## Checklist

1. Branche à jour, `python -m pytest -q` vert dans `Mur contre terre/`.
2. Version : `pyproject.toml` (`version`) et, s'il existe, `__init__.__version__`, mêmes valeurs. Mettre à jour le tableau d'avancement du `README.md` si un lot a changé d'état.
3. Nouvelle dépendance différée (import local dans `bureau.py`, `trace.py`, `export.py`) : l'ajouter à `hidden_imports` dans `mur_contre_terre.spec`, car PyInstaller ne la détecte pas. Ne pas retirer les `excludes` (pandas, scipy, PyQt…).
4. Test local si possible : `pyinstaller mur_contre_terre.spec --noconfirm` puis `dist/MurContreTerre --autotest` (le build final est Windows ; un build Linux ne valide que l'analyse d'imports).
5. Tag : `mur-contre-terre-vX.Y.Z` sur le commit fusionné dans la branche principale. **Pousser un tag publie une release : confirmer avec l'utilisateur avant.**
6. Après le run : vérifier l'étape `--autotest` et la présence de `MurContreTerre-windows.zip` dans la release.

## Pannes fréquentes

- `ModuleNotFoundError` dans l'exe seulement → import différé manquant dans `hidden_imports`.
- Tk/matplotlib absents → `tkinter` et `matplotlib.backends.backend_tkagg` dans `hidden_imports`, extra `[dev]` installé.
- `--autotest` échoue alors que pytest passe → chemin de données/`datas` du spec ou import absolu cassé dans `cli.py`.
