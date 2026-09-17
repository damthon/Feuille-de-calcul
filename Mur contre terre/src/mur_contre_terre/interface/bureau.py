"""Interface de bureau Tkinter — fenêtre à onglets (géométrie, sol, appuis, matériaux, charges, résultats).

Aucun calcul propre : les onglets ne font que remplir des dictionnaires
de champs, traduits vers les dataclasses de calcul par
``interface/saisie.py`` puis passés à ``calcul.calculer()`` — même
charpente qu'annoncée au plan de conception (§10), sur le modèle de
Nommogramme. Sauvegarde/chargement réutilise directement
``donnees.Projet.sauvegarder``/``charger`` (JSON, lot 1).

Chaque onglet de saisie (Géométrie, Sol, Appuis, Matériaux, Charges)
affiche à droite du formulaire un aperçu graphique à l'échelle
(``trace.figure_geometrie``/``figure_section_materiaux``/``figure_charges``,
extra ``[bureau]``, matplotlib) qui se redessine automatiquement — avec un
léger différé (``_debounce``) — à chaque modification d'un champ, pour que
l'utilisateur voie tout de suite l'effet de sa saisie plutôt qu'après coup.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from mur_contre_terre import trace
from mur_contre_terre.calcul import ResultatCalcul, TYPES_CHARGE_AUTOMATIQUES, calculer
from mur_contre_terre.donnees.appuis import ConditionsAppui, TypeAppuiPied, TypeAppuiTete
from mur_contre_terre.donnees.charges import CasDeCharge, TypeCharge
from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.donnees.materiaux import Beton, Materiaux
from mur_contre_terre.donnees.projet import Projet
from mur_contre_terre.donnees.sol import Sol, TypePoussee
from mur_contre_terre.interface import infobulle, saisie
from mur_contre_terre.rapport import generer_note_calcul
from mur_contre_terre.unites import en_deg, en_kN, en_kN_m2, en_kN_m3, en_MPa

TITRE = "Mur contre-terre"

_CLASSES_BETON = ("C20/25", "C25/30", "C30/37", "C35/45", "C40/50")
# Poussée des terres et pression hydrostatique sont désormais générées automatiquement depuis l'onglet
# Sol (voir calcul.charges_effectives) : elles ne figurent plus dans les types sélectionnables ici.
_TYPES_CHARGE = tuple(t.value for t in TypeCharge if t not in TYPES_CHARGE_AUTOMATIQUES)
_CATEGORIES = ("G", "Q", "A")

# Géométrie de repli pour l'aperçu de l'onglet Charges tant que l'onglet Géométrie n'a pas
# (encore) de saisie valide — mêmes valeurs que les champs par défaut de cet onglet.
_GEOMETRIE_PAR_DEFAUT = Geometrie(hauteur=3.0, ep_base=0.30, ep_couronnement=0.20, debord_semelle=0.80, ep_semelle=0.40)

_DELAI_REDESSIN_MS = 250

# Police de base agrandie par rapport au défaut Tk (~9pt) — sans cela, les champs de saisie restent
# minuscules à l'écran une fois la fenêtre maximisée sur un grand moniteur (retour utilisateur).
_POLICE_BASE = ("Segoe UI", 11)
_POLICE_GRAS = ("Segoe UI", 11, "bold")


class Application(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(TITRE)
        self.geometry("1440x900")
        self.minsize(1180, 700)
        self._appliquer_police()

        self.chemin_projet: str | None = None
        self.charges: list[CasDeCharge] = []
        self.indice_charge_en_edition: int | None = None
        self.resultat: ResultatCalcul | None = None
        self.projet_courant: Projet | None = None
        self._apres_ids: dict[str, str] = {}

        self.vars_geometrie: dict[str, tk.StringVar] = {}
        self.vars_sol: dict[str, tk.StringVar] = {}
        self.vars_appuis: dict[str, tk.StringVar] = {}
        self.vars_materiaux: dict[str, tk.StringVar] = {}
        self.vars_charge: dict[str, tk.StringVar] = {}
        self.var_nom_projet = tk.StringVar(value="Nouveau projet")

        self._construire_menu()
        self._construire_onglets()

        # premier tracé des aperçus avec les valeurs par défaut des champs
        self._maj_apercus_mur()
        self._maj_apercu_materiaux()
        self._maj_apercu_charges()

    # ------------------------------------------------------------------ apparence

    def _appliquer_police(self) -> None:
        """Agrandit la police par défaut de tous les widgets (classiques Tk *et* ttk) — l'écran maximisé
        reste lisible même sur un moniteur haute résolution, au lieu de garder la taille système ~9pt."""
        self.option_add("*Font", _POLICE_BASE)
        self.option_add("*TCombobox*Listbox.font", _POLICE_BASE)
        style = ttk.Style(self)
        style.configure(".", font=_POLICE_BASE)
        style.configure("TNotebook.Tab", font=_POLICE_BASE, padding=(14, 8))
        style.configure("Treeview", font=_POLICE_BASE, rowheight=26)
        style.configure("Treeview.Heading", font=_POLICE_GRAS)

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
    ) -> tuple[tk.Label, tk.Entry]:
        label = tk.Label(parent, text=etiquette)
        label.grid(row=ligne, column=0, sticky="w", padx=6, pady=5)
        var = tk.StringVar(value=defaut)
        entree = tk.Entry(parent, textvariable=var, width=16)
        entree.grid(row=ligne, column=1, sticky="w", padx=6, pady=5)
        variables[cle] = var
        if aide:
            infobulle.attacher(entree, aide)
        return label, entree

    def _construire_apercu(self, parent: tk.Widget, largeur: float = 4.3, hauteur: float = 5.3) -> FigureCanvasTkAgg:
        """Panneau d'aperçu graphique (matplotlib intégré) à droite d'un formulaire d'onglet."""
        cadre = tk.Frame(parent, relief="groove", borderwidth=1)
        cadre.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=4)
        canvas = FigureCanvasTkAgg(Figure(figsize=(largeur, hauteur)), master=cadre)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        canvas.draw()
        return canvas

    def _onglet_geometrie(self, notebook: ttk.Notebook) -> tk.Widget:
        cadre = tk.Frame(notebook)
        formulaire = tk.Frame(cadre)
        formulaire.pack(side="left", fill="y", padx=(0, 4), pady=4)

        self._champ(formulaire, 0, "Hauteur H [m]", self.vars_geometrie, "hauteur", "3.0")
        self._champ(formulaire, 1, "Épaisseur en pied [m]", self.vars_geometrie, "ep_base", "0.30")
        self._champ(formulaire, 2, "Épaisseur en tête [m]", self.vars_geometrie, "ep_couronnement", "0.20")
        self._champ(formulaire, 3, "Débord de semelle [m]", self.vars_geometrie, "debord_semelle", "0.80")
        self._champ(formulaire, 4, "Épaisseur de semelle [m]", self.vars_geometrie, "ep_semelle", "0.40")

        self.canvas_geometrie = self._construire_apercu(cadre)
        for var in self.vars_geometrie.values():
            var.trace_add("write", self._on_champ_change_mur)
            var.trace_add("write", self._on_champ_change_materiaux)
            var.trace_add("write", self._on_champ_change_charges)
        return cadre

    def _onglet_sol(self, notebook: ttk.Notebook) -> tk.Widget:
        cadre = tk.Frame(notebook)
        formulaire = tk.Frame(cadre)
        formulaire.pack(side="left", fill="y", padx=(0, 4), pady=4)

        self._champ(formulaire, 0, "Poids volumique γ [kN/m³]", self.vars_sol, "gamma", "18")
        self._champ(formulaire, 1, "Angle de frottement φ′ [°]", self.vars_sol, "phi", "30")
        self._champ(formulaire, 2, "Cohésion c′ [kN/m²]", self.vars_sol, "c", "0")
        self._champ(formulaire, 3, "Inclinaison du terrain β [°]", self.vars_sol, "beta", "0", infobulle.TEXTES["beta"])
        self._champ(formulaire, 4, "Frottement mur-sol δ [°] (vide = auto)", self.vars_sol, "delta", "", infobulle.TEXTES["delta"])

        tk.Label(formulaire, text="Type de poussée").grid(row=5, column=0, sticky="w", padx=6, pady=5)
        self.vars_sol["type_poussee"] = tk.StringVar(value="actif")
        ttk.Combobox(
            formulaire, textvariable=self.vars_sol["type_poussee"], values=("actif", "au_repos"), state="readonly", width=12
        ).grid(row=5, column=1, sticky="w", padx=6, pady=5)

        self._champ(
            formulaire, 6, "Niveau de nappe [m, depuis le pied]", self.vars_sol, "niveau_nappe", "",
            infobulle.TEXTES["niveau_nappe"],
        )
        self._champ(formulaire, 7, "Poids volumique saturé γsat [kN/m³]", self.vars_sol, "gamma_sat", "")
        self._champ(
            formulaire, 8, "Facteur de réduction (écoulement)", self.vars_sol, "facteur_reduction_ecoulement", "1.0",
            infobulle.TEXTES["facteur_reduction_ecoulement"],
        )
        self._champ(formulaire, 9, "Module de réaction ks [MN/m³]", self.vars_sol, "ks", "", infobulle.TEXTES["ks"])

        self.canvas_sol = self._construire_apercu(cadre, largeur=3.6)
        self.canvas_pression = self._construire_apercu(cadre, largeur=3.6)
        for var in self.vars_sol.values():
            var.trace_add("write", self._on_champ_change_mur)
            var.trace_add("write", self._on_champ_change_charges)
        return cadre

    def _onglet_appuis(self, notebook: ttk.Notebook) -> tk.Widget:
        cadre = tk.Frame(notebook)
        formulaire = tk.Frame(cadre)
        formulaire.pack(side="left", fill="y", padx=(0, 4), pady=4)

        tk.Label(formulaire, text="Pied").grid(row=0, column=0, sticky="w", padx=6, pady=5)
        self.vars_appuis["pied"] = tk.StringVar(value="encastrement")
        ttk.Combobox(
            formulaire, textvariable=self.vars_appuis["pied"], values=("encastrement", "ressort"), state="readonly", width=14
        ).grid(row=0, column=1, sticky="w", padx=6, pady=5)

        self._champ(formulaire, 1, "kθ [MN·m/rad] (vide = auto depuis ks)", self.vars_appuis, "k_theta", "", infobulle.TEXTES["k_theta"])

        tk.Label(formulaire, text="Tête").grid(row=2, column=0, sticky="w", padx=6, pady=5)
        self.vars_appuis["tete"] = tk.StringVar(value="libre")
        ttk.Combobox(
            formulaire, textvariable=self.vars_appuis["tete"], values=("libre", "appui_dalle"), state="readonly", width=14
        ).grid(row=2, column=1, sticky="w", padx=6, pady=5)

        self.canvas_appuis = self._construire_apercu(cadre)
        for var in self.vars_appuis.values():
            var.trace_add("write", self._on_champ_change_mur)
        return cadre

    def _onglet_materiaux(self, notebook: ttk.Notebook) -> tk.Widget:
        cadre = tk.Frame(notebook)
        formulaire = tk.Frame(cadre)
        formulaire.pack(side="left", fill="y", padx=(0, 4), pady=4)

        tk.Label(formulaire, text="Classe de béton").grid(row=0, column=0, sticky="w", padx=6, pady=5)
        self.vars_materiaux["classe_beton"] = tk.StringVar(value="C30/37")
        ttk.Combobox(
            formulaire, textvariable=self.vars_materiaux["classe_beton"], values=_CLASSES_BETON, state="readonly", width=12
        ).grid(row=0, column=1, sticky="w", padx=6, pady=5)
        tk.Label(formulaire, text="Acier B500B (fixe)").grid(row=1, column=0, sticky="w", padx=6, pady=5)
        self._champ(formulaire, 2, "Enrobage côté terre [mm]", self.vars_materiaux, "enrobage_terre", "50")
        self._champ(formulaire, 3, "Enrobage côté intérieur [mm]", self.vars_materiaux, "enrobage_interieur", "40")

        self.canvas_materiaux = self._construire_apercu(cadre)
        for var in self.vars_materiaux.values():
            var.trace_add("write", self._on_champ_change_materiaux)
        return cadre

    def _onglet_charges(self, notebook: ttk.Notebook) -> tk.Widget:
        cadre = tk.Frame(notebook)
        gauche = tk.Frame(cadre)
        gauche.pack(side="left", fill="y", padx=(0, 4), pady=4)

        self.liste_charges = tk.Listbox(gauche, height=8, width=46)
        self.liste_charges.grid(row=0, column=0, columnspan=2, padx=4, pady=4, sticky="we")
        self.liste_charges.bind("<Double-Button-1>", lambda _evenement: self._modifier_charge())

        boutons_liste = tk.Frame(gauche)
        boutons_liste.grid(row=1, column=0, columnspan=2, pady=(0, 8))
        tk.Button(boutons_liste, text="Modifier la charge sélectionnée", command=self._modifier_charge).pack(
            side="left", padx=2
        )
        tk.Button(boutons_liste, text="Supprimer la charge sélectionnée", command=self._supprimer_charge).pack(
            side="left", padx=2
        )

        formulaire = tk.LabelFrame(gauche, text="Nouvelle charge")
        formulaire.grid(row=2, column=0, columnspan=2, sticky="we", padx=4)

        self._champ(formulaire, 0, "Nom", self.vars_charge, "nom", "")
        tk.Label(formulaire, text="Type").grid(row=1, column=0, sticky="w", padx=6, pady=5)
        self.vars_charge["type"] = tk.StringVar(value=_TYPES_CHARGE[0])
        ttk.Combobox(
            formulaire, textvariable=self.vars_charge["type"], values=_TYPES_CHARGE, state="readonly", width=28
        ).grid(row=1, column=1, sticky="w", padx=6, pady=5)
        tk.Label(formulaire, text="Catégorie").grid(row=2, column=0, sticky="w", padx=6, pady=5)
        self.vars_charge["categorie"] = tk.StringVar(value="G")
        ttk.Combobox(
            formulaire, textvariable=self.vars_charge["categorie"], values=_CATEGORIES, state="readonly", width=6
        ).grid(row=2, column=1, sticky="w", padx=6, pady=5)
        self.etiquette_valeur, self.entree_valeur = self._champ(formulaire, 3, "Valeur", self.vars_charge, "valeur", "0")
        self._champ(formulaire, 4, "ψ0", self.vars_charge, "psi0", "0", infobulle.TEXTES["psi0"])
        self._champ(formulaire, 5, "ψ1", self.vars_charge, "psi1", "0", infobulle.TEXTES["psi1"])
        self._champ(formulaire, 6, "ψ2", self.vars_charge, "psi2", "0", infobulle.TEXTES["psi2"])
        self._lignes_parametres_charge: dict[str, tuple[tk.Label, tk.Entry]] = {
            "excentricite": self._champ(formulaire, 7, "Excentricité [m]", self.vars_charge, "excentricite", ""),
            "distance": self._champ(formulaire, 8, "Distance au mur [m]", self.vars_charge, "distance", ""),
            "etendue": self._champ(formulaire, 9, "Étendue [m]", self.vars_charge, "etendue", ""),
            "profondeur_application": self._champ(
                formulaire, 10, "Profondeur d'application [m]", self.vars_charge, "profondeur_application", ""
            ),
        }

        boutons_formulaire = tk.Frame(formulaire)
        boutons_formulaire.grid(row=11, column=0, columnspan=2, pady=6)
        self.bouton_charge = tk.Button(boutons_formulaire, text="Ajouter la charge", command=self._ajouter_charge)
        self.bouton_charge.pack(side="left", padx=2)
        self.bouton_annuler_edition = tk.Button(
            boutons_formulaire, text="Annuler la modification", command=self._annuler_edition_charge
        )
        # masqué tant qu'on n'édite pas une charge existante (voir _modifier_charge)

        self.canvas_charges = self._construire_apercu(cadre)
        for var in self.vars_charge.values():
            var.trace_add("write", self._on_champ_change_charges)
        self.vars_charge["type"].trace_add("write", self._maj_champs_charge)
        self._maj_champs_charge()
        return cadre

    def _onglet_resultats(self, notebook: ttk.Notebook) -> tk.Widget:
        cadre = tk.Frame(notebook)
        barre = tk.Frame(cadre)
        barre.pack(fill="x", pady=4)
        tk.Button(barre, text="Calculer", command=self._calculer).pack(side="left", padx=4)
        tk.Button(barre, text="Exporter en Markdown…", command=self._exporter_note).pack(side="left", padx=4)
        tk.Button(barre, text="Exporter en PDF…", command=self._exporter_pdf).pack(side="left", padx=4)
        tk.Button(barre, text="Exporter en Excel…", command=self._exporter_excel).pack(side="left", padx=4)
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

    # ------------------------------------------------------------ aperçus graphiques

    def _construire_geometrie_ou_none(self) -> Geometrie | None:
        try:
            return saisie.geometrie_depuis_champs({c: v.get() for c, v in self.vars_geometrie.items()})
        except ValueError:
            return None

    def _construire_sol_ou_none(self) -> Sol | None:
        try:
            return saisie.sol_depuis_champs({c: v.get() for c, v in self.vars_sol.items()})
        except ValueError:
            return None

    def _construire_appuis_ou_none(self) -> ConditionsAppui | None:
        try:
            return saisie.appuis_depuis_champs({c: v.get() for c, v in self.vars_appuis.items()})
        except ValueError:
            return None

    def _construire_materiaux_ou_none(self) -> Materiaux | None:
        try:
            return saisie.materiaux_depuis_champs({c: v.get() for c, v in self.vars_materiaux.items()})
        except ValueError:
            return None

    def _dessiner(self, canvas: FigureCanvasTkAgg, construire_figure: Callable[[], Figure]) -> None:
        """Remplace la figure d'un aperçu par une nouvelle, en libérant l'ancienne. Silencieux si la
        saisie en cours ne permet pas encore de construire un projet valide (champ vide, non numérique…)."""
        try:
            nouvelle_figure = construire_figure()
        except Exception:
            return
        ancienne_figure = canvas.figure
        canvas.figure = nouvelle_figure
        canvas.draw_idle()
        if ancienne_figure is not nouvelle_figure:
            plt.close(ancienne_figure)

    def _maj_apercus_mur(self) -> None:
        """Aperçu commun aux onglets Géométrie/Sol/Appuis : coupe du mur, massif de terre/nappe, appuis ;
        et, dans l'onglet Sol, profil de pression horizontale (poussée des terres + hydrostatique)."""
        geometrie = self._construire_geometrie_ou_none()
        if geometrie is None:
            return
        sol = self._construire_sol_ou_none()
        appuis = self._construire_appuis_ou_none()
        for canvas in (self.canvas_geometrie, self.canvas_sol, self.canvas_appuis):
            self._dessiner(canvas, lambda g=geometrie, s=sol, a=appuis: trace.figure_geometrie(g, s, a))
        if sol is not None:
            self._dessiner(self.canvas_pression, lambda g=geometrie, s=sol: trace.figure_pression_sol(s, g))

    def _maj_apercu_materiaux(self) -> None:
        geometrie = self._construire_geometrie_ou_none()
        materiaux = self._construire_materiaux_ou_none()
        if geometrie is None or materiaux is None:
            return
        self._dessiner(self.canvas_materiaux, lambda g=geometrie, m=materiaux: trace.figure_section_materiaux(g, m))

    def _maj_apercu_charges(self) -> None:
        geometrie = self._construire_geometrie_ou_none() or _GEOMETRIE_PAR_DEFAUT
        sol = self._construire_sol_ou_none()
        try:
            previsualisation = saisie.charge_depuis_champs({c: v.get() for c, v in self.vars_charge.items()})
        except ValueError:
            previsualisation = None
        charges = list(self.charges)
        self._dessiner(
            self.canvas_charges,
            lambda g=geometrie, s=sol, ch=charges, p=previsualisation: trace.figure_charges(g, s, ch, p),
        )

    def _debounce(self, cle: str, fonction: Callable[[], None]) -> None:
        """Retarde ``fonction`` de ``_DELAI_REDESSIN_MS`` : évite de redessiner à chaque frappe clavier."""
        identifiant = self._apres_ids.pop(cle, None)
        if identifiant is not None:
            self.after_cancel(identifiant)
        self._apres_ids[cle] = self.after(_DELAI_REDESSIN_MS, fonction)

    def _on_champ_change_mur(self, *_args: object) -> None:
        self._debounce("mur", self._maj_apercus_mur)

    def _on_champ_change_materiaux(self, *_args: object) -> None:
        self._debounce("materiaux", self._maj_apercu_materiaux)

    def _on_champ_change_charges(self, *_args: object) -> None:
        self._debounce("charges", self._maj_apercu_charges)

    def _maj_champs_charge(self, *_args: object) -> None:
        """Affiche uniquement les champs (Valeur, paramètres) pertinents pour le type de charge
        sélectionné — ex. distance/étendue n'ont pas de sens pour un poids propre (voir
        ``saisie.PARAMETRES_PAR_TYPE``). Appelé immédiatement (pas de _debounce) au changement de type."""
        try:
            type_charge = TypeCharge(self.vars_charge["type"].get())
        except ValueError:
            return

        if type_charge in saisie.TYPES_AVEC_VALEUR:
            unite = saisie.UNITE_AFFICHEE_VALEUR.get(type_charge, "")
            self.etiquette_valeur.config(text=f"Valeur [{unite}]" if unite else "Valeur")
            self.etiquette_valeur.grid()
            self.entree_valeur.grid()
        else:
            self.etiquette_valeur.grid_remove()
            self.entree_valeur.grid_remove()
            self.vars_charge["valeur"].set("0")

        parametres_utilises = saisie.PARAMETRES_PAR_TYPE.get(type_charge, ())
        for cle, (etiquette, entree) in self._lignes_parametres_charge.items():
            if cle in parametres_utilises:
                etiquette.grid()
                entree.grid()
            else:
                etiquette.grid_remove()
                entree.grid_remove()
                self.vars_charge[cle].set("")

    # ----------------------------------------------------------------- actions

    def _resume_charge(self, charge: CasDeCharge) -> str:
        return f"{charge.nom} ({charge.type.value}, {charge.categorie.value})"

    def _ajouter_charge(self) -> None:
        try:
            charge = saisie.charge_depuis_champs({cle: var.get() for cle, var in self.vars_charge.items()})
        except ValueError as erreur:
            messagebox.showerror("Charge invalide", str(erreur))
            return
        if self.indice_charge_en_edition is not None:
            indice = self.indice_charge_en_edition
            self.charges[indice] = charge
            self.liste_charges.delete(indice)
            self.liste_charges.insert(indice, self._resume_charge(charge))
            self._annuler_edition_charge()
        else:
            self.charges.append(charge)
            self.liste_charges.insert("end", self._resume_charge(charge))
        self._maj_apercu_charges()

    def _modifier_charge(self) -> None:
        selection = self.liste_charges.curselection()
        if not selection:
            messagebox.showinfo("Aucune sélection", "Sélectionnez d'abord une charge dans la liste à modifier.")
            return
        indice = selection[0]
        self.indice_charge_en_edition = indice
        for cle, valeur in saisie.champs_depuis_charge(self.charges[indice]).items():
            self.vars_charge[cle].set(valeur)
        self.bouton_charge.config(text="Mettre à jour la charge")
        self.bouton_annuler_edition.pack(side="left", padx=2)

    def _annuler_edition_charge(self) -> None:
        self.indice_charge_en_edition = None
        self.bouton_charge.config(text="Ajouter la charge")
        self.bouton_annuler_edition.pack_forget()

    def _supprimer_charge(self) -> None:
        selection = self.liste_charges.curselection()
        if not selection:
            return
        indice = selection[0]
        self.liste_charges.delete(indice)
        del self.charges[indice]
        if self.indice_charge_en_edition == indice:
            self._annuler_edition_charge()
        elif self.indice_charge_en_edition is not None and self.indice_charge_en_edition > indice:
            self.indice_charge_en_edition -= 1
        self._maj_apercu_charges()

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

    def _resultat_disponible(self) -> bool:
        if self.projet_courant is None or self.resultat is None:
            messagebox.showwarning("Aucun résultat", "Lancez d'abord un calcul (bouton « Calculer »).")
            return False
        return True

    def _exporter_note(self) -> None:
        if not self._resultat_disponible():
            return
        chemin = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown", "*.md")])
        if not chemin:
            return
        with open(chemin, "w", encoding="utf-8") as fichier:
            fichier.write(generer_note_calcul(self.projet_courant, self.resultat))

    def _exporter_pdf(self) -> None:
        if not self._resultat_disponible():
            return
        chemin = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not chemin:
            return
        try:
            from mur_contre_terre.export import exporter_pdf

            exporter_pdf(self.projet_courant, self.resultat, chemin)
        except ImportError:
            messagebox.showerror(
                "Extra manquant", "L'export PDF nécessite l'extra [export] : pip install -e \".[export]\""
            )

    def _exporter_excel(self) -> None:
        if not self._resultat_disponible():
            return
        chemin = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if not chemin:
            return
        try:
            from mur_contre_terre.export import exporter_excel

            exporter_excel(self.projet_courant, self.resultat, chemin)
        except ImportError:
            messagebox.showerror(
                "Extra manquant", "L'export Excel nécessite l'extra [export] : pip install -e \".[export]\""
            )

    def _nouveau(self) -> None:
        self.charges.clear()
        self.liste_charges.delete(0, "end")
        self._annuler_edition_charge()
        self.resultat = None
        self.projet_courant = None
        self.chemin_projet = None
        self.var_nom_projet.set("Nouveau projet")
        self._maj_apercu_charges()

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
        self._annuler_edition_charge()
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

        # poussée des terres/pression hydrostatique : plus une charge gérée manuellement (voir
        # TYPES_CHARGE_AUTOMATIQUES) — un fichier .mct antérieur à ce changement peut encore en porter,
        # elles sont donc filtrées ici plutôt que de rester dans la liste sans être modifiables.
        self.charges = [c for c in projet.charges if c.type not in TYPES_CHARGE_AUTOMATIQUES]
        self.liste_charges.delete(0, "end")
        for charge in self.charges:
            self.liste_charges.insert("end", self._resume_charge(charge))
        self._maj_apercu_charges()

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
