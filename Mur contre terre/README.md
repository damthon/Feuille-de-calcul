# Mur contre-terre

Vérification et dimensionnement d'un mur de sous-sol de bâtiment en béton
armé, fondé sur une semelle filante avant. Modèle poutre aux éléments
finis sur toute la hauteur du mur, poussée des terres selon **SIA 261 /
267** (Coulomb), vérification en section **SIA 262** (flexion composée,
effort tranchant), avec prise en compte de la non-linéarité matérielle
(fissuration du béton, plastification des aciers) pour le calcul des
déplacements.

La stabilité d'ensemble (renversement, glissement) n'est pas traitée : elle
est assurée par le bâtiment. Seule la résistance structurale du mur (ELU
type 2) est vérifiée.

L'architecture et le mode de distribution reprennent ceux de
[Nommogramme](https://github.com/damthon/Nommogramme) — voir
[`docs/plan-conception.html`](docs/plan-conception.html) pour le plan de
conception complet (architecture, structures de données, schémas du
modèle, méthode de calcul de la poussée des terres) et
[`Prompt Claude.txt`](Prompt%20Claude.txt) pour le cahier des charges
d'origine.

## État d'avancement

| Lot | Contenu | État |
|:---:|---|:---:|
| 1 | Structures de données, unités, sérialisation JSON du projet | fait |
| 2 | Poussée des terres (Coulomb), hydrostatique, compactage | fait |
| 3 | Maillage, rigidité élémentaire, appuis, solveur linéaire | fait |
| 4 | Combinaisons SIA 260, charges nodales équivalentes | fait |
| 5 | Lois de matériaux avancées, flexion composée, effort tranchant | fait |
| 6 | Moment-courbure, EI sécant, encastrement élastique kθ | fait |
| 7 | Solveur incrémental non linéaire | fait |
| 8 | Note de calcul, figures | fait |
| 9 | Interface de bureau, sauvegarde/chargement de projet | fait |
| 10 | Export PDF / Excel | fait |
| 11 | Empaquetage exécutable Windows, CI | fait |
| 12 | Validation contre les cas de référence Excel du bureau | à venir |

## Installation

```bash
cd "Mur contre terre"
python -m venv .venv
source .venv/bin/activate        # Windows : .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m pytest
```

Python 3.11 ou plus récent. Dépendance obligatoire à l'exécution :
`numpy` (algèbre linéaire du maillage). `matplotlib` (extra `[trace]`),
`openpyxl` et `reportlab` (extra `[export]`) ne servent qu'aux figures et
à l'export des résultats.

## Utilisation comme bibliothèque (lot 1)

```python
from mur_contre_terre import (
    Acier, Beton, CasDeCharge, CategorieAction, ConditionsAppui,
    Geometrie, Materiaux, Projet, Sol, TypeAppuiPied, TypeAppuiTete,
    TypeCharge, TypePoussee,
)
from mur_contre_terre.unites import deg, kN, kN_m3, MPa

projet = Projet(
    nom="Mur de sous-sol — bâtiment X",
    geometrie=Geometrie(
        hauteur=3.0, ep_base=0.30, ep_couronnement=0.20,
        debord_semelle=0.80, ep_semelle=0.40,
    ),
    sol=Sol(
        gamma=kN_m3(18), phi=deg(30), delta=deg(20),
        type_poussee=TypePoussee.ACTIF, ks=MPa(0.03),
    ),
    appuis=ConditionsAppui(pied=TypeAppuiPied.RESSORT, tete=TypeAppuiTete.APPUI_DALLE),
    materiaux=Materiaux(
        beton=Beton.depuis_classe("C30/37"), acier=Acier.b500b(),
        enrobage_terre=0.05, enrobage_interieur=0.04,
    ),
    charges=(
        CasDeCharge(
            nom="Charge en tête", type=TypeCharge.CHARGE_TETE,
            categorie=CategorieAction.G, valeur=kN(80),
            parametres={"excentricite": 0.05},
        ),
    ),
    finesse_maillage=0.25,
)

projet.sauvegarder("mon_projet.mct")
relu = Projet.charger("mon_projet.mct")
```

Toutes les structures de données (`Geometrie`, `Sol`, `ConditionsAppui`,
`Materiaux`, `CasDeCharge`, `Projet`) sont des `@dataclass(frozen=True)` :
un calcul ne modifie jamais ses entrées. Les unités internes sont
strictement SI (m, N, Pa, rad) ; `unites.py` fournit les conversions depuis
kN, kNm, MPa, kN/m², kN/m³ et degrés.

## Hypothèses du modèle (lot 1)

- Modèle plan, tranche de 1,00 m de longueur de mur.
- Épaisseur du mur interpolée linéairement entre la base et le
  couronnement.
- La rigidité en rotation de l'encastrement élastique au pied est
  kθ = ks·B³/12 (Winkler), B étant la largeur totale de la semelle.
- Coefficient de poussée active Kah (Coulomb) et au repos K0 (Jaky,
  terrain incliné), avec cohésion et plancher e_ah,k ≥ 5 kN/m² selon
  SIA 261 §4.3.2 — voir [`docs/plan-conception.html`](docs/plan-conception.html) §7.
- Pression hydrostatique triangulaire depuis le niveau de nappe, réduite
  par un facteur d'écoulement ; pression de compactage en plateau constant
  sur les x premiers mètres (modèle simplifié, à affiner au lot 12).
- Rigidité en rotation kθ = ks·B³/12 (Winkler) et contrôle de compression
  intégrale de la semelle (e ≤ B/6).
- Éléments poutre d'Euler-Bernoulli verticaux (pas de transformation de
  repère), section évaluée au milieu de chaque élément ; convention de
  signe N/V/M calibrée et vérifiée contre des solutions fermées de RDM —
  voir l'en-tête de [`mecanique/solveur_lineaire.py`](src/mur_contre_terre/mecanique/solveur_lineaire.py).
- Aucun calcul de stabilité d'ensemble (renversement, glissement).

## Utilisation — poussée des terres (lot 2)

```python
from mur_contre_terre.geotechnique import profil_poussee, pression_hydrostatique
from mur_contre_terre.donnees import Sol, TypePoussee
from mur_contre_terre.unites import deg, kN_m3

sol = Sol(gamma=kN_m3(18), phi=deg(30), type_poussee=TypePoussee.ACTIF)
e_ah, e_av = profil_poussee(sol, hauteur=3.0, profondeur=3.0)  # Pa, au pied du mur
```

## Utilisation — solveur mécanique (lot 3)

```python
import numpy as np
from mur_contre_terre.mecanique import generer_maillage, rigidites_par_element, resoudre

maillage = generer_maillage(projet.geometrie, projet.finesse_maillage)
ea, ei = rigidites_par_element(projet.geometrie, projet.materiaux, maillage)

forces = np.zeros(maillage.nb_dof)
forces[3 * (maillage.nb_noeuds - 1) + 1] = 10_000.0  # charge horizontale en tête [N]

resultat = resoudre(maillage, ea, ei, projet.appuis, projet.sol, projet.geometrie, forces)
resultat.deplacements       # (nb_noeuds, 3) : w, u, θ
resultat.moment_flechissant  # (nb_elements, 2) : M(début), M(fin)
```

## Utilisation — charges nodales et combinaisons (lot 4)

```python
from mur_contre_terre.mecanique import (
    generer_combinaisons_elu, rigidites_par_element, resoudre, vecteur_charge, vecteur_combine,
)

maillage = generer_maillage(projet.geometrie, projet.finesse_maillage)
ea, ei = rigidites_par_element(projet.geometrie, projet.materiaux, maillage)

vecteurs = {
    c.nom: vecteur_charge(c, projet.sol, projet.geometrie, projet.materiaux, maillage)
    for c in projet.charges
}

for combinaison in generer_combinaisons_elu(projet.charges):
    F = vecteur_combine(combinaison, vecteurs)
    resultat = resoudre(maillage, ea, ei, projet.appuis, projet.sol, projet.geometrie, F)
```

Convention de signe (voir l'en-tête de
[`mecanique/charges_nodales.py`](src/mur_contre_terre/mecanique/charges_nodales.py)) :
`+u` pointe du côté terre vers l'intérieur (sens de poussée du mur),
`+w` pointe vers le haut. `SURCHARGE_TETE` et `POUSSEE_TERRES` restent deux
actions distinctes malgré la formule commune (§4.3.2.3), pour que chacune
garde son propre facteur de combinaison.

La charge surfacique et la charge linéaire sur le terre-plein utilisent une
formule élastique (Boussinesq, paroi rigide) faute de clause SIA fournie —
comme la pression de compactage, à confirmer au lot 12.

## Utilisation — section béton armé (lot 5)

```python
from mur_contre_terre.section_ba import SectionRectangulaire, armature_necessaire, resistance_effort_tranchant

section = SectionRectangulaire(epaisseur=0.30, enrobage_terre=0.05, enrobage_interieur=0.04)

# M_Ed > 0 tend la face intérieure, M_Ed < 0 tend la face terre (voir flexion_composee.py)
resultat = armature_necessaire(
    n_ed=-150e3, m_ed=80e3, section=section, materiaux=projet.materiaux, face_tendue="interieur",
)
resultat.armature_necessaire  # [m²/m] — max(armature calculée, armature minimale normative)

v_rd = resistance_effort_tranchant(
    projet.materiaux.beton, largeur=1.0, hauteur_utile=0.26, taux_armature=0.003,
)
```

Lois de matériaux (`section_ba/modele_beton.py`, `modele_acier.py`) :
parabole-rectangle en compression + traction linéaire jusqu'à fissuration
pour le béton, bilinéaire écrouissable pour l'acier B500B — SIA 262 §4.1.
`armature_necessaire` résout par bissection l'équilibre de section
(compatibilité des déformations, fibre extrême comprimée à −εcu) pour
trouver l'aire d'armature tendue qui équilibre exactement (N_Ed, M_Ed) ;
le résultat retient le plus grand de cette valeur et de l'armature
minimale normative.

La résistance à l'effort tranchant (`effort_tranchant.py`) utilise la
formule harmonisée EN 1992-1-1 §6.2.2, faute d'extrait SIA 262 §4.3.3
vérifié — comme la pression de compactage et les charges de terre-plein,
à confirmer au lot 12.

## Utilisation — moment-courbure (lot 6)

```python
from mur_contre_terre.section_ba import courbe_moment_courbure, rigidite_non_fissuree

# armature fixe (contrairement à armature_necessaire, qui la dimensionne) ;
# sens=+1 trace la flexion qui tend la face intérieure (χ > 0), sens=-1 la face terre
courbe = courbe_moment_courbure(
    n_ed=-150e3, section=section, materiaux=projet.materiaux,
    armature_terre=8e-4, armature_interieur=8e-4, sens=1, nb_paliers=20,
)
courbe[-1].chi   # courbure de rupture (écrasement du béton ou rupture de l'acier)
courbe[0].ei_secant  # rigidité sécante EI = M/χ, décroissante avec la fissuration
```

`moment_courbure.py` résout, pour une courbure χ croissante et un effort
normal N maintenu constant, la déformation de référence ε0 qui équilibre
N (bissection), jusqu'à ce qu'une fibre de béton atteigne −εcu ou qu'un
lit d'armature atteigne ±εud. C'est la rigidité sécante EI(x) que le
solveur incrémental non linéaire (lot 7) mettra à jour à chaque palier de
charge le long de la hauteur du mur.

## Utilisation — solveur incrémental non linéaire (lot 7)

```python
from mur_contre_terre.nonlineaire import resoudre_incremental

resultat = resoudre_incremental(
    maillage, geometrie, projet.materiaux, projet.appuis, projet.sol,
    forces_nodales=F,  # vecteur à 100 % de charge (un des vecteurs de charges nodales du lot 4)
    armature_terre=6e-4, armature_interieur=6e-4,  # [m²/m], scalaire ou un tableau par élément
    nb_paliers=20, tolerance=1e-3, max_iterations=30,
)
resultat.convergence_totale        # False si la structure ne reprend pas 100 % de la charge
resultat.fraction_charge_maximale  # dernier palier convergé
resultat.paliers[-1].resultat.deplacements  # comme mecanique.resoudre, au dernier palier
```

`nonlineaire/solveur_incremental.py` orchestre `mecanique/` et
`section_ba/` : à chaque palier de charge, K est assemblée avec l'EI(x)
courant de chaque élément (EA reste à sa valeur élastique de section
brute, seul EI est mis à jour — §9 du plan) ; les efforts internes du
palier déterminent une nouvelle rigidité sécante par
`section_ba.moment_courbure.rigidite_secante`, jusqu'à convergence ou,
si une section dépasse sa résistance, arrêt du chargement (le dernier
palier convergé est la charge maximale atteinte sous cette hypothèse
d'armature). `moment_courbure.py` utilise les résistances
caractéristiques (fck/fsk), pas les résistances de calcul ELU (fcd/fsd)
de `flexion_composee.py` : ce module vise une réponse M-χ réaliste
(déplacements, charge de ruine), pas une marge de sécurité normative —
voir la note en tête de fichier pour la légère dissymétrie résiduelle de
tangente initiale que cela laisse (≈ 9 % à très faible courbure).

Cette recherche par bissections imbriquées (matériaux non linéaires,
pas de solveur analytique) reste coûteuse : un maillage de 6 éléments
sur 20 paliers prend de l'ordre de la minute sur une machine courante.
Un profil plus fin (nb_paliers, max_iterations) ou une meilleure
stratégie d'accélération pourront être revus ultérieurement si
nécessaire.

## Utilisation — calcul complet et note de calcul (lot 8)

```python
from mur_contre_terre.calcul import calculer
from mur_contre_terre.rapport import generer_note_calcul

resultat = calculer(projet)          # maillage → charges → combinaisons ELU/ELS → vérification de section
resultat.verifications               # une VerificationSection par élément : armature + effort tranchant
md = generer_note_calcul(projet, resultat)
open("note_de_calcul.md", "w").write(md)
```

`calcul.py` est la première couche du dépôt à connaître à la fois
`mecanique/` et `section_ba/` — c'est l'orchestration bout en bout
(maillage, charges nodales par cas, combinaisons SIA 260, résolution
linéaire par combinaison, puis armature nécessaire et effort tranchant
par élément, enveloppe des combinaisons ELU). Elle ne couvre pas encore
la non-linéarité matérielle (`nonlineaire.resoudre_incremental`, à
appeler séparément) ni l'export PDF/Excel (lot 10).

`trace.py` (extra `[trace]`, matplotlib) fournit les figures —
géométrie, diagrammes N/V/M, moment-courbure, déformée — chacune
retournée comme `matplotlib.figure.Figure` à enregistrer ou intégrer
par l'appelant.

## Utilisation — interface de bureau et ligne de commande (lot 9)

```bash
mur-contre-terre                                   # lance l'interface de bureau (Tkinter)
mur-contre-terre verifier projet.mct                # calcule et affiche la note de calcul
mur-contre-terre verifier projet.mct -o note.md      # … ou l'écrit dans un fichier
```

`interface/bureau.py` (Tkinter, extra `[bureau]` pour matplotlib) ouvre
une fenêtre à onglets (géométrie, sol, appuis, matériaux, charges,
résultats) ; `interface/saisie.py` porte la seule traduction entre les
champs (unités utilisateur : m, °, kN, kN/m², kN/m³, MPa) et les
dataclasses de calcul — testée sans Tkinter. Sauvegarde/chargement de
projet réutilise directement `Projet.sauvegarder`/`Projet.charger`
(JSON `.mct`, lot 1). `cli.py` fournit le point d'entrée
(`mur-contre-terre`, voir `[project.scripts]`) : sans sous-commande il
lance l'interface, sinon `verifier` calcule un projet sans fenêtre —
c'est aussi la base de l'exécutable empaqueté (lot 11, `--autotest`).

Chaque onglet de saisie affiche à droite du formulaire un aperçu
graphique à l'échelle (`trace.figure_geometrie` pour Géométrie/Sol/Appuis
— coupe du mur, massif de terre retenu, niveau de nappe, symboles
d'appui ; `trace.figure_section_materiaux` pour Matériaux — enrobages
cotés ; `trace.figure_charges` pour Charges — une flèche par charge
appliquée, coloriée selon la catégorie d'action G/Q/A, plus un aperçu en
pointillés de la charge en cours de saisie avant son ajout) qui se
redessine automatiquement, avec un léger différé, à chaque modification
d'un champ. Dans l'onglet Charges, la liste des charges déjà ajoutées se
double-clique (ou bouton « Modifier la charge sélectionnée ») pour
recharger ses valeurs dans le formulaire et les corriger, plutôt que de
devoir la supprimer puis la ressaisir.

Tkinter fait partie de la bibliothèque standard mais n'est pas toujours
présent dans un environnement de développement minimal (ex. `python3-tk`
manquant) ; `conftest.py` ignore alors `interface/bureau.py` et
`interface/infobulle.py` à la collecte des tests plutôt que de faire
échouer toute la suite — une installation Python standard (Windows,
macOS) ou l'exécutable empaqueté l'incluent tous deux.

## Utilisation — export PDF et Excel (lot 10)

```python
from mur_contre_terre.export import exporter_excel, exporter_pdf

exporter_excel(projet, resultat, "note_de_calcul.xlsx")
exporter_pdf(projet, resultat, "note_de_calcul.pdf")
```

```bash
mur-contre-terre verifier projet.mct -o note.pdf    # format déduit de l'extension
mur-contre-terre verifier projet.mct -o note.xlsx
```

`export.py` (extra `[export]` : `openpyxl`, `reportlab`) réutilise
`ResultatCalcul` directement, comme `rapport.py` — aucun des trois ne
recalcule quoi que ce soit. PDF via `reportlab` (bibliothèque pure
Python) plutôt que `weasyprint` (dépendances système natives
Cairo/Pango/GTK) : plus simple à empaqueter de façon fiable avec
PyInstaller (lot 11). L'interface de bureau propose les trois formats
(Markdown, PDF, Excel) depuis l'onglet Résultats.

## Exécutable Windows et intégration continue (lot 11)

`mur_contre_terre.spec` (racine du dépôt) empaquette `cli.py` avec
PyInstaller en un exécutable Windows unique (`MurContreTerre.exe`,
partagé CLI/GUI — voir `cli.py`). Deux workflows GitHub Actions :

- [`tests.yml`](../.github/workflows/tests.yml) : suite de tests
  complète (`pytest`, avec `python3-tk` et `xvfb`) à chaque push/PR
  touchant ce dossier.
- [`build-release.yml`](../.github/workflows/build-release.yml) :
  au push d'un tag `mur-contre-terre-v*` (ou déclenchement manuel),
  construit l'exécutable sur `windows-latest`, le vérifie
  (`MurContreTerre.exe --autotest` — mêmes imports différés que
  matplotlib Tk chez Nommogramme), puis publie une release GitHub avec
  `MurContreTerre-windows.zip` en pièce jointe.

Construction locale (Windows, ou toute plateforme pour du
débogage) :

```bash
cd "Mur contre terre"
pip install -e ".[dev]"
pip install pyinstaller
pyinstaller mur_contre_terre.spec --noconfirm
./dist/MurContreTerre --autotest        # .\dist\MurContreTerre.exe sous Windows
```

## Avertissement

Ce dépôt est en développement (lot 11 sur 12). Le lot 12 (validation
contre les cas de référence Excel du bureau d'ingénieurs) reste à
faire — il nécessite les cas de référence de l'utilisateur, non
disponibles à ce stade. **Ne pas utiliser ce dépôt pour une
justification de projet réelle sans cette validation**, et en gardant
à l'esprit les points explicitement signalés comme non confirmés dans
ce document (résistance à l'effort tranchant, charges de terre-plein,
pression de compactage — voir les sections correspondantes ci-dessus).
