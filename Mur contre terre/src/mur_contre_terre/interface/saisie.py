"""Traduction unique entre les champs de saisie (unités utilisateur) et les dataclasses de calcul.

Aucune autre partie de l'interface ne construit de dataclass de calcul
directement — ``mecanique``/``section_ba``/etc. ne connaissent ni ce
module ni Tkinter (§3 du plan de conception : « l'interface ne fait que
traduire des champs de saisie vers des objets ``donnees/`` »). Toutes
les fonctions ci-dessous sont pures (aucun import Tkinter) : elles
prennent des ``Mapping[str, str]`` — le contenu brut de widgets de
saisie (``Entry``/``Combobox``), avant toute mise en forme — et
retournent soit une dataclass de calcul, soit lèvent ``ValueError``
avec un message destiné à être affiché à l'écran (nom du champ en
français, pas de nom de paramètre Python).

Unités attendues dans les champs (converties ici vers le SI interne) :
longueurs en m, angles en degrés, poids volumiques en kN/m³, pressions/
contraintes/cohésion en kN/m², résistances en MPa, forces ponctuelles en
kN, le module de réaction ks en MN/m³ (= MPa/m, même ordre de grandeur
que les classes de béton — réutilise ``unites.MPa``), les charges
linéiques du terre-plein en kN/m (réutilise ``unites.kN`` : la
conversion kN→N et kN/m→N/m est le même facteur ×1000).
"""

from __future__ import annotations

from collections.abc import Mapping

from mur_contre_terre.donnees.appuis import ConditionsAppui, TypeAppuiPied, TypeAppuiTete
from mur_contre_terre.donnees.charges import CasDeCharge, CategorieAction, TypeCharge
from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.donnees.materiaux import Acier, Beton, Materiaux
from mur_contre_terre.donnees.sol import Sol, TypePoussee
from mur_contre_terre.unites import deg, en_kN, en_kN_m2, kN, kN_m2, kN_m3, MPa

# Type de charge -> conversion à appliquer à CasDeCharge.parametres["valeur"] (kN, kN/m ou kN/m²).
# POUSSEE_TERRES et PRESSION_HYDROSTATIQUE sont calculées depuis Sol/Geometrie : valeur ignorée (0.0 attendu).
_UNITE_VALEUR = {
    TypeCharge.POIDS_PROPRE: None,  # calculée automatiquement (mecanique.charges_nodales.poids_propre)
    TypeCharge.CHARGE_TETE: kN,
    TypeCharge.POUSSEE_TERRES: None,
    TypeCharge.SURCHARGE_TETE: kN_m2,
    TypeCharge.CHARGE_SURFACIQUE_TERREPLEIN: kN_m2,
    TypeCharge.CHARGE_LINEAIRE_TERREPLEIN: kN,  # kN/m — même facteur ×1000 que kN()
    TypeCharge.PRESSION_HYDROSTATIQUE: None,
    TypeCharge.PRESSION_COMPACTAGE: kN_m2,
}

# Inverse de _UNITE_VALEUR — reconstruit la valeur en unités utilisateur depuis le SI (voir champs_depuis_charge).
_UNITE_VALEUR_INVERSE = {
    TypeCharge.POIDS_PROPRE: None,
    TypeCharge.CHARGE_TETE: en_kN,
    TypeCharge.POUSSEE_TERRES: None,
    TypeCharge.SURCHARGE_TETE: en_kN_m2,
    TypeCharge.CHARGE_SURFACIQUE_TERREPLEIN: en_kN_m2,
    TypeCharge.CHARGE_LINEAIRE_TERREPLEIN: en_kN,
    TypeCharge.PRESSION_HYDROSTATIQUE: None,
    TypeCharge.PRESSION_COMPACTAGE: en_kN_m2,
}

# Types pour lesquels le champ « Valeur » est utilisé (les autres sont calculés automatiquement — voir
# _UNITE_VALEUR — et l'interface peut donc masquer ce champ sans perte d'information).
TYPES_AVEC_VALEUR = frozenset(t for t, conversion in _UNITE_VALEUR.items() if conversion is not None)

# Unité affichée à côté du champ « Valeur », propre à chaque type de charge.
UNITE_AFFICHEE_VALEUR: dict[TypeCharge, str] = {
    TypeCharge.CHARGE_TETE: "kN",
    TypeCharge.SURCHARGE_TETE: "kN/m²",
    TypeCharge.CHARGE_SURFACIQUE_TERREPLEIN: "kN/m²",
    TypeCharge.CHARGE_LINEAIRE_TERREPLEIN: "kN/m",
    TypeCharge.PRESSION_COMPACTAGE: "kN/m²",
}

# Paramètres (``CasDeCharge.parametres``) réellement exploités pour chaque type de charge — voir
# ``mecanique.charges_nodales.vecteur_charge`` — pour que l'interface n'affiche que les champs utilisables
# selon le type sélectionné plutôt que la totalité des paramètres possibles (n.b. ``SURCHARGE_TETE`` module la
# poussée sur toute la hauteur du massif via ``g0`` : distance/étendue ne s'y appliquent pas).
PARAMETRES_PAR_TYPE: dict[TypeCharge, tuple[str, ...]] = {
    TypeCharge.POIDS_PROPRE: (),
    TypeCharge.CHARGE_TETE: ("excentricite",),
    TypeCharge.POUSSEE_TERRES: (),
    TypeCharge.SURCHARGE_TETE: (),
    TypeCharge.CHARGE_SURFACIQUE_TERREPLEIN: ("distance", "etendue"),
    TypeCharge.CHARGE_LINEAIRE_TERREPLEIN: ("distance",),
    TypeCharge.PRESSION_HYDROSTATIQUE: (),
    TypeCharge.PRESSION_COMPACTAGE: ("profondeur_application",),
}


def _formater(valeur: float) -> str:
    """Représentation compacte d'un nombre pour un champ de saisie (pas de zéros superflus)."""
    return f"{valeur:g}"


def _champ(champs: Mapping[str, str], cle: str) -> str:
    return champs.get(cle, "").strip().replace(",", ".")


def _float(champs: Mapping[str, str], cle: str, nom_affiche: str) -> float:
    brute = _champ(champs, cle)
    if not brute:
        raise ValueError(f"{nom_affiche} : champ requis")
    try:
        return float(brute)
    except ValueError:
        raise ValueError(f"{nom_affiche} : valeur numérique attendue (reçu {champs[cle]!r})") from None


def _float_optionnel(champs: Mapping[str, str], cle: str, nom_affiche: str) -> float | None:
    return _float(champs, cle, nom_affiche) if _champ(champs, cle) else None


def geometrie_depuis_champs(champs: Mapping[str, str]) -> Geometrie:
    return Geometrie(
        hauteur=_float(champs, "hauteur", "Hauteur H"),
        ep_base=_float(champs, "ep_base", "Épaisseur en pied"),
        ep_couronnement=_float(champs, "ep_couronnement", "Épaisseur en tête"),
        debord_semelle=_float(champs, "debord_semelle", "Débord de semelle"),
        ep_semelle=_float(champs, "ep_semelle", "Épaisseur de semelle"),
    )


def sol_depuis_champs(champs: Mapping[str, str]) -> Sol:
    type_poussee_brute = champs.get("type_poussee", "actif")
    type_poussee = TypePoussee.ACTIF if type_poussee_brute == "actif" else TypePoussee.AU_REPOS

    gamma_sat_kn = _float_optionnel(champs, "gamma_sat", "Poids volumique saturé γsat")
    delta_deg = _float_optionnel(champs, "delta", "Frottement mur-sol δ")
    niveau_nappe = _float_optionnel(champs, "niveau_nappe", "Niveau de nappe")
    ks_mpa = _float_optionnel(champs, "ks", "Module de réaction ks")
    facteur_ecoulement = _float_optionnel(champs, "facteur_reduction_ecoulement", "Facteur de réduction (écoulement)")

    return Sol(
        gamma=kN_m3(_float(champs, "gamma", "Poids volumique γ")),
        phi=deg(_float(champs, "phi", "Angle de frottement φ′")),
        c=kN_m2(_float(champs, "c", "Cohésion c′")) if _champ(champs, "c") else 0.0,
        beta=deg(_float(champs, "beta", "Inclinaison du terrain β")) if _champ(champs, "beta") else 0.0,
        gamma_sat=kN_m3(gamma_sat_kn) if gamma_sat_kn is not None else None,
        delta=deg(delta_deg) if delta_deg is not None else None,
        rugueux=champs.get("rugueux", "oui") != "non",
        type_poussee=type_poussee,
        niveau_nappe=niveau_nappe,
        facteur_reduction_ecoulement=facteur_ecoulement if facteur_ecoulement is not None else 1.0,
        ks=MPa(ks_mpa) if ks_mpa is not None else None,
    )


def materiaux_depuis_champs(champs: Mapping[str, str]) -> Materiaux:
    classe_beton = champs.get("classe_beton", "").strip()
    if not classe_beton:
        raise ValueError("Classe de béton : champ requis")
    return Materiaux(
        beton=Beton.depuis_classe(classe_beton),
        acier=Acier.b500b(),
        enrobage_terre=_float(champs, "enrobage_terre", "Enrobage côté terre") / 1000.0,
        enrobage_interieur=_float(champs, "enrobage_interieur", "Enrobage côté intérieur") / 1000.0,
    )


def appuis_depuis_champs(champs: Mapping[str, str]) -> ConditionsAppui:
    pied_brut = champs.get("pied", "encastrement")
    pied = TypeAppuiPied.RESSORT if pied_brut == "ressort" else TypeAppuiPied.ENCASTREMENT
    tete_brut = champs.get("tete", "libre")
    tete = TypeAppuiTete.APPUI_DALLE if tete_brut == "appui_dalle" else TypeAppuiTete.LIBRE
    k_theta_mnm = _float_optionnel(champs, "k_theta", "Rigidité en rotation kθ (saisie manuelle)")
    return ConditionsAppui(pied=pied, tete=tete, k_theta=MPa(k_theta_mnm) if k_theta_mnm is not None else None)


def charge_depuis_champs(champs: Mapping[str, str]) -> CasDeCharge:
    """``champs`` porte ``nom``, ``type`` (valeur de ``TypeCharge``), ``categorie`` (G/Q/A), ``valeur``,
    ``psi0``/``psi1``/``psi2`` et les paramètres propres au type (``excentricite``, ``distance``,
    ``etendue``, ``profondeur_application`` — déjà en mètres, aucune conversion requise)."""
    nom = champs.get("nom", "").strip()
    if not nom:
        raise ValueError("Nom de la charge : champ requis")
    try:
        type_charge = TypeCharge(champs.get("type", ""))
    except ValueError:
        raise ValueError(f"Type de charge inconnu : {champs.get('type')!r}") from None
    try:
        categorie = CategorieAction(champs.get("categorie", ""))
    except ValueError:
        raise ValueError(f"Catégorie d'action inconnue : {champs.get('categorie')!r}") from None

    conversion = _UNITE_VALEUR[type_charge]
    valeur_brute = _float(champs, "valeur", "Valeur") if conversion is not None else 0.0
    valeur = conversion(valeur_brute) if conversion is not None else 0.0

    parametres: dict[str, float] = {}
    for cle in ("excentricite", "distance", "etendue", "profondeur_application"):
        if _champ(champs, cle):
            parametres[cle] = _float(champs, cle, cle)

    return CasDeCharge(
        nom=nom,
        type=type_charge,
        categorie=categorie,
        valeur=valeur,
        psi0=_float(champs, "psi0", "ψ0") if _champ(champs, "psi0") else 0.0,
        psi1=_float(champs, "psi1", "ψ1") if _champ(champs, "psi1") else 0.0,
        psi2=_float(champs, "psi2", "ψ2") if _champ(champs, "psi2") else 0.0,
        parametres=parametres,
    )


def champs_depuis_charge(charge: CasDeCharge) -> dict[str, str]:
    """Inverse de ``charge_depuis_champs`` : reconstruit les champs de saisie (unités utilisateur)
    d'une ``CasDeCharge`` existante, pour pré-remplir le formulaire lors de sa modification."""
    conversion = _UNITE_VALEUR_INVERSE[charge.type]
    valeur = conversion(charge.valeur) if conversion is not None else 0.0
    champs = {
        "nom": charge.nom,
        "type": charge.type.value,
        "categorie": charge.categorie.value,
        "valeur": _formater(valeur),
        "psi0": _formater(charge.psi0),
        "psi1": _formater(charge.psi1),
        "psi2": _formater(charge.psi2),
    }
    for cle in ("excentricite", "distance", "etendue", "profondeur_application"):
        champs[cle] = _formater(charge.parametres[cle]) if cle in charge.parametres else ""
    return champs
