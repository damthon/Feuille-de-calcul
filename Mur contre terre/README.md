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
| 4 | Combinaisons SIA 260, charges nodales équivalentes | à venir |
| 5 | Lois de matériaux avancées, flexion composée, effort tranchant | à venir |
| 6 | Moment-courbure, EI sécant, encastrement élastique kθ | à venir |
| 7 | Solveur incrémental non linéaire | à venir |
| 8 | Note de calcul, figures | à venir |
| 9 | Interface de bureau, sauvegarde/chargement de projet | à venir |
| 10 | Export PDF / Excel | à venir |
| 11 | Empaquetage exécutable Windows, CI | à venir |
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

Les charges nodales équivalentes à partir des diagrammes de pression
(`geotechnique`) et des combinaisons SIA 260 arrivent au lot 4 — pour
l'instant le solveur prend un vecteur de charges nodales déjà construit.

## Avertissement

Ce dépôt est en développement (lot 3 sur 12). Les charges nodales
équivalentes (poussée des terres → vecteur F), les combinaisons SIA 260,
la vérification de section et les résultats ne sont pas encore
implémentés. Ne pas utiliser en l'état pour une justification de projet.
