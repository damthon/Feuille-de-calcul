# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller .spec — MurContreTerre.exe (lot 11).

Construit un exécutable Windows one-file autour de ``cli.py`` (lance
l'interface de bureau sans argument, ou une vérification en ligne de
commande — voir son en-tête). matplotlib (backend Tk) et certains
sous-modules chargés à la volée par openpyxl/reportlab sont des
dépendances différées (imports locaux dans bureau.py/trace.py/export.py,
jamais au niveau module) : l'analyse statique de PyInstaller ne les
détecte pas — ils sont déclarés explicitement ci-dessous
(``hiddenimports``), comme le fait Nommogramme pour son propre .spec.

Construit par ``.github/workflows/build-release.yml`` sur un runner
Windows, au push d'un tag ``mur-contre-terre-v*`` : ``pyinstaller
mur_contre_terre.spec``, puis ``--autotest`` avant publication.
"""

hidden_imports = [
    "tkinter",
    "matplotlib.backends.backend_tkagg",
    "PIL._tkinter_finder",
    "openpyxl.cell._writer",
    "reportlab.graphics.barcode",
]

a = Analysis(
    ["src/mur_contre_terre/cli.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Lourdeurs inutiles à un exécutable de bureau (§3 du plan de conception) — jamais importées
    # par ce paquet, mais parfois entraînées par l'analyse statique via des dépendances tierces.
    excludes=["pandas", "pyarrow", "scipy", "PyQt5", "PySide2", "IPython", "notebook"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MurContreTerre",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # partagé CLI (verifier, --autotest) / GUI (sans argument) — voir cli.py
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
