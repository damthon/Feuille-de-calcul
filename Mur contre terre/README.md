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
| 2 | Poussée des terres (Coulomb), hydrostatique, compactage | à venir |
| 3 | Maillage, rigidité élémentaire, appuis, solveur linéaire | à venir |
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
- Coefficients de poussée des terres Kah/Kph par la méthode de Coulomb ;
  formulation complète (cohésion, K0 pour terrain incliné) au lot 2, voir
  [`docs/plan-conception.html`](docs/plan-conception.html) §7.
- Aucun calcul de stabilité d'ensemble (renversement, glissement).

## Avertissement

Ce dépôt est en développement (lot 1 sur 12). Aucun calcul de poussée des
terres, de résistance de section ou de résultat n'est encore implémenté.
Ne pas utiliser en l'état pour une justification de projet.
