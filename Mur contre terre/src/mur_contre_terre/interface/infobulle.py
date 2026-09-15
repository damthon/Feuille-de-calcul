"""Infobulle (tooltip) au survol — aide contextuelle pour les champs de saisie (δ, β, ψ, κ…).

Implémentation minimale sans dépendance tierce : une fenêtre ``Toplevel``
sans décoration, positionnée sous le widget survolé, affichée après un
court délai et masquée dès que la souris quitte le widget.
"""

from __future__ import annotations

import tkinter as tk

DELAI_MS = 500


class Infobulle:
    """Attache une infobulle de texte ``texte`` au widget ``widget``, affichée au survol."""

    def __init__(self, widget: tk.Widget, texte: str) -> None:
        self.widget = widget
        self.texte = texte
        self._apres_id: str | None = None
        self._fenetre: tk.Toplevel | None = None
        widget.bind("<Enter>", self._sur_entree, add="+")
        widget.bind("<Leave>", self._sur_sortie, add="+")
        widget.bind("<ButtonPress>", self._sur_sortie, add="+")

    def _sur_entree(self, _evenement: object = None) -> None:
        self._apres_id = self.widget.after(DELAI_MS, self._afficher)

    def _sur_sortie(self, _evenement: object = None) -> None:
        if self._apres_id is not None:
            self.widget.after_cancel(self._apres_id)
            self._apres_id = None
        self._masquer()

    def _afficher(self) -> None:
        if self._fenetre is not None:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self._fenetre = fenetre = tk.Toplevel(self.widget)
        fenetre.wm_overrideredirect(True)
        fenetre.wm_geometry(f"+{x}+{y}")
        etiquette = tk.Label(
            fenetre, text=self.texte, justify="left", background="#FFFFE0", relief="solid", borderwidth=1,
            padx=6, pady=3, font=("TkDefaultFont", 9), wraplength=320,
        )
        etiquette.pack()

    def _masquer(self) -> None:
        if self._fenetre is not None:
            self._fenetre.destroy()
            self._fenetre = None


def attacher(widget: tk.Widget, texte: str) -> Infobulle:
    """Raccourci : ``attacher(champ_delta, TEXTES["delta"])``."""
    return Infobulle(widget, texte)


TEXTES: dict[str, str] = {
    "delta": "δ — frottement mur-sol. Par défaut, 2φ′/3 (paroi rugueuse) ou 0 (paroi lisse) — SIA 261 §4.3.2.3.",
    "beta": "β — inclinaison du terrain derrière le mur (0° = horizontal).",
    "psi0": "ψ0 — coefficient de combinaison ELU pour une action variable non dominante (SIA 260 tableau 3).",
    "psi1": "ψ1 — coefficient ELS fréquent pour l'action variable dominante.",
    "psi2": "ψ2 — coefficient ELS quasi permanent pour les actions variables non dominantes.",
    "ks": "ks — module de réaction du sol [MN/m³], pour l'encastrement élastique au pied (kθ = ks·B³/12).",
    "k_theta": (
        "kθ — rigidité en rotation de l'encastrement élastique, saisie manuelle [MN·m/rad] "
        "(remplace le calcul automatique depuis ks)."
    ),
    "niveau_nappe": "Niveau de la nappe phréatique, mesuré depuis le pied du mur [m].",
    "facteur_reduction_ecoulement": (
        "Facteur de réduction de la pression hydrostatique par écoulement autour du pied (1 = aucune réduction)."
    ),
    "rugueux": "Paroi rugueuse (contact béton coulé contre terre) : valeur par défaut de δ = 2φ′/3.",
}
