"""Interface de bureau Tkinter — fenêtre à onglets (géométrie, sol, appuis, matériaux, charges, résultats).

Aucun calcul propre : les onglets ne font que remplir des dictionnaires
de champs, traduits vers les dataclasses de calcul par
``interface/saisie.py`` puis passés à ``calcul.calculer()`` — même
charpente qu'annoncée au plan de conception (§10), sur le modèle de
Nommogramme. Sauvegarde/chargement réutilise directement
``donnees.Projet.sauvegarder``/``charger`` (JSON, lot 1).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from mur_contre_terre.calcul import ResultatCalcul, calculer
from mur_contre_terre.donnees.appuis import TypeAppuiPied, TypeAppuiTete
from mur_contre_terre.donnees.charges import CasDeCharge, TypeCharge
from mur_contre_terre.donnees.materiaux import Beton
from mur_contre_terre.donnees.projet import Projet
from mur_contre_terre.donnees.sol import TypePoussee
from mur_contre_terre.interface import infobulle, saisie
from mur_contre_terre.rapport import generer_note_calcul
from mur_contre_terre.unites import en_deg, en_kN, en_kN_m2, en_kN_m3, en_MPa

TITRE = "Mur contre-terre"

_CLASSES_BETON = ("C20/25", "C25/30", "C30/37", "C35/45", "C40/50")
_TYPES_CHARGE = tuple(t.value for t in TypeCharge)
_CATEGORIES = ("G", "Q", "A")


class Application(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(TITRE)
        self.geometry("920x680")

        self.chemin_projet: str | None = None
        self.charges: list[CasDeCharge] = []
        self.resultat: ResultatCalcul | None = None
        self.projet_courant: Projet | None = None

        self.vars_geometrie: dict[str, tk.StringVar] = {}
        self.vars_sol: dict[str, tk.StringVar] = {}
        self.vars_appuis: dict[str, tk.StringVar] = {}
        self.vars_materiaux: dict[str, tk.StringVar] = {}
        self.vars_charge: dict[str, tk.StringVar] = {}
        self.var_nom_projet = tk.StringVar(value="Nouveau projet")

        self._construire_menu()
        self._construire_onglets()

    # ------------------------------------------------------------------ menu

    def _construire_menu(self) -> None:
        menu = tk.Menu(self)
        fichier = tk.Menu(menu, tearoff=False)
        fichier.add_command(label="Nouveau", command=self._nouveau)
        fichier.add_command(label="Ouvrir…", command=self._ouvrir)
        fichier.add_command(label="Enregistrer sous…", command=self._enregistrer_sous)
        fichier.add_separator()
        fichier.add_command(label="Quitter", command=self.destroy)
        menu.add_cascade(label="Fichier", menu=fichier)
        self.config(menu=menu)

    # --------------------------------------------------------------- onglets

    def _construire_onglets(self) -> None:
        entete = tk.Frame(self)
        entete.pack(fill="x", padx=8, pady=(8, 0))
        tk.Label(entete, text="Nom du projet :").pack(side="left")
        tk.Entry(entete, textvariable=self.var_nom_projet, width=40).pack(side="left", padx=6)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        notebook.add(self._onglet_geometrie(notebook), text="Géométrie")
        notebook.add(self._onglet_sol(notebook), text="Sol")
        notebook.add(self._onglet_appuis(notebook), text="Appuis")
        notebook.add(self._onglet_materiaux(notebook), text="Matériaux")
        notebook.add(self._onglet_charges(notebook), text="Charges")
        notebook.add(self._onglet_resultats(notebook), text="Résultats")

    def _champ(
        self,
        parent: tk.Widget,
        ligne: int,
        etiquette: str,
        variables: dict[str, tk.StringVar],
        cle: str,
        defaut: str = "",
        aide: str | None = None,
    ) -> tk.Entry:
        tk.Label(parent, text=etiquette).grid(row=ligne, column=0, sticky="w", padx=4, pady=3)
        var = tk.StringVar(value=defaut)
        entree = tk.Entry(parent, textvariable=var, width=14)
        entree.grid(row=ligne, column=1, sticky="w", padx=4, pady=3)
        variables[cle] = var
        if aide:
            infobulle.attacher(entree, aide)
        return entree

    def _onglet_geometrie(self, notebook: ttk.Notebook) -> tk.Widget:
        cadre = tk.Frame(notebook)
        self._champ(cadre, 0, "Hauteur H [m]", self.vars_geometrie, "hauteur", "3.0")
        self._champ(cadre, 1, "Épaisseur en pied [m]", self.vars_geometrie, "ep_base", "0.30")
        self._champ(cadre, 2, "Épaisseur en tête [m]", self.vars_geometrie, "ep_couronnement", "0.20")
        self._champ(cadre, 3, "Débord de semelle [m]", self.vars_geometrie, "debord_semelle", "0.80")
        self._champ(cadre, 4, "Épaisseur de semelle [m]", self.vars_geometrie, "ep_semelle", "0.40")
        return cadre

    def _onglet_sol(self, notebook: ttk.Notebook) -> tk.Widget:
        cadre = tk.Frame(notebook)
        self._champ(cadre, 0, "Poids volumique γ [kN/m³]", self.vars_sol, "gamma", "18")
        self._champ(cadre, 1, "Angle de frottement φ′ [°]", self.vars_sol, "phi", "30")
        self._champ(cadre, 2, "Cohésion c′ [kN/m²]", self.vars_sol, "c", "0")
        self._champ(cadre, 3, "Inclinaison du terrain β [°]", self.vars_sol, "beta", "0", infobulle.TEXTES["beta"])
        self._champ(cadre, 4, "Frottement mur-sol δ [°] (vide = auto)", self.vars_sol, "delta", "", infobulle.TEXTES["delta"])

        tk.Label(cadre, text="Type de poussée").grid(row=5, column=0, sticky="w", padx=4, pady=3)
        self.vars_sol["type_poussee"] = tk.StringVar(value="actif")
        ttk.Combobox(
            cadre, textvariable=self.vars_sol["type_poussee"], values=("actif", "au_repos"), state="readonly", width=12
        ).grid(row=5, column=1, sticky="w", padx=4, pady=3)

        self._champ(
            cadre, 6, "Niveau de nappe [m, depuis le pied]", self.vars_sol, "niveau_nappe", "",
            infobulle.TEXTES["niveau_nappe"],
        )
        self._champ(cadre, 7, "Poids volumique saturé γsat [kN/m³]", self.vars_sol, "gamma_sat", "")
        self._champ(
            cadre, 8, "Facteur de réduction (écoulement)", self.vars_sol, "facteur_reduction_ecoulement", "1.0",
            infobulle.TEXTES["facteur_reduction_ecoulement"],
        )
        self._champ(cadre, 9, "Module de réaction ks [MN/m³]", self.vars_sol, "ks", "", infobulle.TEXTES["ks"])
        return cadre

    def _onglet_appuis(self, notebook: ttk.Notebook) -> tk.Widget:
        cadre = tk.Frame(notebook)
        tk.Label(cadre, text="Pied").grid(row=0, column=0, sticky="w", padx=4, pady=3)
        self.vars_appuis["pied"] = tk.StringVar(value="encastrement")
        ttk.Combobox(
            cadre, textvariable=self.vars_appuis["pied"], values=("encastrement", "ressort"), state="readonly", width=14
        ).grid(row=0, column=1, sticky="w", padx=4, pady=3)

        self._champ(cadre, 1, "kθ [MN·m/rad] (vide = auto depuis ks)", self.vars_appuis, "k_theta", "", infobulle.TEXTES["k_theta"])

        tk.Label(cadre, text="Tête").grid(row=2, column=0, sticky="w", padx=4, pady=3)
        self.vars_appuis["tete"] = tk.StringVar(value="libre")
        ttk.Combobox(
            cadre, textvariable=self.vars_appuis["tete"], values=("libre", "appui_dalle"), state="readonly", width=14
        ).grid(row=2, column=1, sticky="w", padx=4, pady=3)
        return cadre

    def _onglet_materiaux(self, notebook: ttk.Notebook) -> tk.Widget:
        cadre = tk.Frame(notebook)
        tk.Label(cadre, text="Classe de béton").grid(row=0, column=0, sticky="w", padx=4, pady=3)
        self.vars_materiaux["classe_beton"] = tk.StringVar(value="C30/37")
        ttk.Combobox(
            cadre, textvariable=self.vars_materiaux["classe_beton"], values=_CLASSES_BETON, state="readonly", width=12
        ).grid(row=0, column=1, sticky="w", padx=4, pady=3)
        tk.Label(cadre, text="Acier B500B (fixe)").grid(row=1, column=0, sticky="w", padx=4, pady=3)
        self._champ(cadre, 2, "Enrobage côté terre [mm]", self.vars_materiaux, "enrobage_terre", "50")
        self._champ(cadre, 3, "Enrobage côté intérieur [mm]", self.vars_materiaux, "enrobage_interieur", "40")
        return cadre

    def _onglet_charges(self, notebook: ttk.Notebook) -> tk.Widget:
        cadre = tk.Frame(notebook)

        self.liste_charges = tk.Listbox(cadre, height=8, width=70)
        self.liste_charges.grid(row=0, column=0, columnspan=2, padx=4, pady=4, sticky="we")
        tk.Button(cadre, text="Supprimer la charge sélectionnée", command=self._supprimer_charge).grid(
            row=1, column=0, columnspan=2, pady=(0, 8)
        )

        formulaire = tk.LabelFrame(cadre, text="Nouvelle charge")
        formulaire.grid(row=2, column=0, columnspan=2, sticky="we", padx=4)

        self._champ(formulaire, 0, "Nom", self.vars_charge, "nom", "")
        tk.Label(formulaire, text="Type").grid(row=1, column=0, sticky="w", padx=4, pady=3)
        self.vars_charge["type"] = tk.StringVar(value=_TYPES_CHARGE[0])
        ttk.Combobox(
            formulaire, textvariable=self.vars_charge["type"], values=_TYPES_CHARGE, state="readonly", width=28
        ).grid(row=1, column=1, sticky="w", padx=4, pady=3)
        tk.Label(formulaire, text="Catégorie").grid(row=2, column=0, sticky="w", padx=4, pady=3)
        self.vars_charge["categorie"] = tk.StringVar(value="G")
        ttk.Combobox(
            formulaire, textvariable=self.vars_charge["categorie"], values=_CATEGORIES, state="readonly", width=6
        ).grid(row=2, column=1, sticky="w", padx=4, pady=3)
        self._champ(formulaire, 3, "Valeur", self.vars_charge, "valeur", "0")
        self._champ(formulaire, 4, "ψ0", self.vars_charge, "psi0", "0", infobulle.TEXTES["psi0"])
        self._champ(formulaire, 5, "ψ1", self.vars_charge, "psi1", "0", infobulle.TEXTES["psi1"])
        self._champ(formulaire, 6, "ψ2", self.vars_charge, "psi2", "0", infobulle.TEXTES["psi2"])
        self._champ(formulaire, 7, "Excentricité [m]", self.vars_charge, "excentricite", "")
        self._champ(formulaire, 8, "Distance au mur [m]", self.vars_charge, "distance", "")
        self._champ(formulaire, 9, "Étendue [m]", self.vars_charge, "etendue", "")
        self._champ(formulaire, 10, "Profondeur d'application [m]", self.vars_charge, "profondeur_application", "")

        tk.Button(formulaire, text="Ajouter la charge", command=self._ajouter_charge).grid(
            row=11, column=0, columnspan=2, pady=6
        )
        return cadre

    def _onglet_resultats(self, notebook: ttk.Notebook) -> tk.Widget:
        cadre = tk.Frame(notebook)
        barre = tk.Frame(cadre)
        barre.pack(fill="x", pady=4)
        tk.Button(barre, text="Calculer", command=self._calculer).pack(side="left", padx=4)
        tk.Button(barre, text="Exporter la note de calcul (.md)…", command=self._exporter_note).pack(side="left", padx=4)
        self.label_statut = tk.Label(barre, text="", fg="#A8391A")
        self.label_statut.pack(side="left", padx=8)

        colonnes = ("z", "h", "as_terre", "as_interieur", "v_ed", "v_rd", "verdict")
        self.tableau_resultats = ttk.Treeview(cadre, columns=colonnes, show="headings", height=14)
        entetes = {
            "z": "z [m]", "h": "h [cm]", "as_terre": "As terre [cm²/m]", "as_interieur": "As int. [cm²/m]",
            "v_ed": "V_Ed [kN]", "v_rd": "V_Rd [kN]", "verdict": "Effort tranchant",
        }
        for cle in colonnes:
            self.tableau_resultats.heading(cle, text=entetes[cle])
            self.tableau_resultats.column(cle, width=110, anchor="center")
        self.tableau_resultats.pack(fill="both", expand=True, padx=4, pady=4)
        return cadre

    # ----------------------------------------------------------------- actions

    def _ajouter_charge(self) -> None:
        try:
            charge = saisie.charge_depuis_champs({cle: var.get() for cle, var in self.vars_charge.items()})
        except ValueError as erreur:
            messagebox.showerror("Charge invalide", str(erreur))
            return
        self.charges.append(charge)
        self.liste_charges.insert("end", f"{charge.nom} ({charge.type.value}, {charge.categorie.value})")

    def _supprimer_charge(self) -> None:
        selection = self.liste_charges.curselection()
        if not selection:
            return
        indice = selection[0]
        self.liste_charges.delete(indice)
        del self.charges[indice]

    def _construire_projet(self) -> Projet | None:
        try:
            geometrie = saisie.geometrie_depuis_champs({c: v.get() for c, v in self.vars_geometrie.items()})
            sol = saisie.sol_depuis_champs({c: v.get() for c, v in self.vars_sol.items()})
            appuis = saisie.appuis_depuis_champs({c: v.get() for c, v in self.vars_appuis.items()})
            materiaux = saisie.materiaux_depuis_champs({c: v.get() for c, v in self.vars_materiaux.items()})
            return Projet(
                nom=self.var_nom_projet.get() or "Projet sans nom",
                geometrie=geometrie, sol=sol, appuis=appuis, materiaux=materiaux, charges=tuple(self.charges),
            )
        except ValueError as erreur:
            messagebox.showerror("Saisie invalide", str(erreur))
            return None

    def _calculer(self) -> None:
        projet = self._construire_projet()
        if projet is None:
            return
        try:
            resultat = calculer(projet)
        except Exception as erreur:  # affichage d'erreur, pas de plantage silencieux de l'interface
            messagebox.showerror("Erreur de calcul", str(erreur))
            return

        self.projet_courant = projet
        self.resultat = resultat
        self.label_statut.config(text="")
        self.tableau_resultats.delete(*self.tableau_resultats.get_children())
        for v in resultat.verifications:
            self.tableau_resultats.insert(
                "", "end",
                values=(
                    f"{v.position:.2f}", f"{v.epaisseur * 100:.1f}", f"{v.armature_terre * 1e4:.2f}",
                    f"{v.armature_interieur * 1e4:.2f}", f"{en_kN(v.effort_tranchant_ed):.1f}",
                    f"{en_kN(v.effort_tranchant_rd):.1f}", "OK" if v.verdict_tranchant else "Insuffisant",
                ),
            )

    def _exporter_note(self) -> None:
        if self.projet_courant is None or self.resultat is None:
            messagebox.showwarning("Aucun résultat", "Lancez d'abord un calcul (bouton « Calculer »).")
            return
        chemin = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown", "*.md")])
        if not chemin:
            return
        with open(chemin, "w", encoding="utf-8") as fichier:
            fichier.write(generer_note_calcul(self.projet_courant, self.resultat))

    def _nouveau(self) -> None:
        self.charges.clear()
        self.liste_charges.delete(0, "end")
        self.resultat = None
        self.projet_courant = None
        self.chemin_projet = None
        self.var_nom_projet.set("Nouveau projet")

    def _ouvrir(self) -> None:
        chemin = filedialog.askopenfilename(filetypes=[("Projet mur contre-terre", "*.mct"), ("Tous les fichiers", "*")])
        if not chemin:
            return
        try:
            projet = Projet.charger(chemin)
        except (OSError, ValueError) as erreur:
            messagebox.showerror("Impossible d'ouvrir le projet", str(erreur))
            return
        self._charger_projet(projet)
        self.chemin_projet = chemin

    def _charger_projet(self, projet: Projet) -> None:
        self.var_nom_projet.set(projet.nom)

        g = projet.geometrie
        self.vars_geometrie["hauteur"].set(str(g.hauteur))
        self.vars_geometrie["ep_base"].set(str(g.ep_base))
        self.vars_geometrie["ep_couronnement"].set(str(g.ep_couronnement))
        self.vars_geometrie["debord_semelle"].set(str(g.debord_semelle))
        self.vars_geometrie["ep_semelle"].set(str(g.ep_semelle))

        s = projet.sol
        self.vars_sol["gamma"].set(str(en_kN_m3(s.gamma)))
        self.vars_sol["phi"].set(str(en_deg(s.phi)))
        self.vars_sol["c"].set(str(en_kN_m2(s.c)))
        self.vars_sol["beta"].set(str(en_deg(s.beta)))
        self.vars_sol["delta"].set(str(en_deg(s.delta)) if s.delta is not None else "")
        self.vars_sol["type_poussee"].set("actif" if s.type_poussee is TypePoussee.ACTIF else "au_repos")
        self.vars_sol["niveau_nappe"].set(str(s.niveau_nappe) if s.niveau_nappe is not None else "")
        self.vars_sol["gamma_sat"].set(str(en_kN_m3(s.gamma_sat)) if s.gamma_sat is not None else "")
        self.vars_sol["facteur_reduction_ecoulement"].set(str(s.facteur_reduction_ecoulement))
        self.vars_sol["ks"].set(str(en_MPa(s.ks)) if s.ks is not None else "")

        a = projet.appuis
        self.vars_appuis["pied"].set("ressort" if a.pied is TypeAppuiPied.RESSORT else "encastrement")
        self.vars_appuis["tete"].set("appui_dalle" if a.tete is TypeAppuiTete.APPUI_DALLE else "libre")
        self.vars_appuis["k_theta"].set(str(en_MPa(a.k_theta)) if a.k_theta is not None else "")

        m = projet.materiaux
        self.vars_materiaux["classe_beton"].set(next((c for c in _CLASSES_BETON if Beton.depuis_classe(c).fck == m.beton.fck), "C30/37"))
        self.vars_materiaux["enrobage_terre"].set(str(m.enrobage_terre * 1000.0))
        self.vars_materiaux["enrobage_interieur"].set(str(m.enrobage_interieur * 1000.0))

        self.charges = list(projet.charges)
        self.liste_charges.delete(0, "end")
        for charge in self.charges:
            self.liste_charges.insert("end", f"{charge.nom} ({charge.type.value}, {charge.categorie.value})")

    def _enregistrer_sous(self) -> None:
        projet = self._construire_projet()
        if projet is None:
            return
        chemin = filedialog.asksaveasfilename(defaultextension=".mct", filetypes=[("Projet mur contre-terre", "*.mct")])
        if not chemin:
            return
        projet.sauvegarder(chemin)
        self.chemin_projet = chemin


def lancer() -> None:
    """Point d'entrée de l'interface de bureau (voir ``cli.py``)."""
    Application().mainloop()


if __name__ == "__main__":
    lancer()
