"""Ignore les modules Tkinter à la collecte (``--doctest-modules``) si tkinter n'est pas installé.

``python3-tk`` (ou équivalent) n'est pas systématiquement présent dans
tous les environnements de développement — contrairement à une
installation Python standard (Windows, macOS) ou à l'exécutable
empaqueté (lot 11), qui l'incluent tous deux. Sans ce garde-fou, son
absence casserait la collecte pytest pour tout le paquet, pas
seulement pour l'interface de bureau.
"""

import importlib.util

collect_ignore_glob: list[str] = []
if importlib.util.find_spec("tkinter") is None:
    collect_ignore_glob += [
        "src/mur_contre_terre/interface/bureau.py",
        "src/mur_contre_terre/interface/infobulle.py",
    ]
