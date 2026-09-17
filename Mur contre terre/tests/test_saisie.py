import pytest

from mur_contre_terre.donnees.appuis import TypeAppuiPied, TypeAppuiTete
from mur_contre_terre.donnees.charges import CategorieAction, TypeCharge
from mur_contre_terre.donnees.sol import TypePoussee
from mur_contre_terre.interface.saisie import (
    appuis_depuis_champs,
    champs_depuis_charge,
    charge_depuis_champs,
    geometrie_depuis_champs,
    materiaux_depuis_champs,
    sol_depuis_champs,
)
from mur_contre_terre.unites import MPa, en_deg, en_kN, en_kN_m2, en_kN_m3, en_MPa


def test_geometrie_depuis_champs():
    g = geometrie_depuis_champs(
        {"hauteur": "3.0", "ep_base": "0.30", "ep_couronnement": "0.20", "debord_semelle": "0.8", "ep_semelle": "0.4"}
    )
    assert g.hauteur == pytest.approx(3.0)
    assert g.ep_base == pytest.approx(0.30)


def test_geometrie_depuis_champs_accepte_la_virgule_decimale():
    g = geometrie_depuis_champs(
        {"hauteur": "3,0", "ep_base": "0,30", "ep_couronnement": "0.20", "debord_semelle": "0.8", "ep_semelle": "0.4"}
    )
    assert g.hauteur == pytest.approx(3.0)


def test_geometrie_depuis_champs_champ_manquant_leve_une_erreur_lisible():
    with pytest.raises(ValueError, match="Hauteur H"):
        geometrie_depuis_champs({"ep_base": "0.3", "ep_couronnement": "0.2", "debord_semelle": "0.8", "ep_semelle": "0.4"})


def test_geometrie_depuis_champs_valeur_non_numerique_leve_une_erreur_lisible():
    with pytest.raises(ValueError, match="Hauteur H"):
        geometrie_depuis_champs(
            {"hauteur": "abc", "ep_base": "0.3", "ep_couronnement": "0.2", "debord_semelle": "0.8", "ep_semelle": "0.4"}
        )


def test_sol_depuis_champs_conversions_d_unite():
    s = sol_depuis_champs({"gamma": "18", "phi": "30", "c": "5", "beta": "10"})
    assert s.gamma == pytest.approx(18e3)
    assert en_deg(s.phi) == pytest.approx(30.0)
    assert en_kN_m2(s.c) == pytest.approx(5.0)
    assert en_deg(s.beta) == pytest.approx(10.0)


def test_sol_depuis_champs_champs_optionnels_absents_donnent_none_ou_defaut():
    s = sol_depuis_champs({"gamma": "18", "phi": "30"})
    assert s.c == 0.0
    assert s.beta == 0.0
    assert s.gamma_sat is None
    assert s.delta is None
    assert s.niveau_nappe is None
    assert s.ks is None
    assert s.facteur_reduction_ecoulement == pytest.approx(1.0)


def test_sol_depuis_champs_type_poussee_au_repos():
    s = sol_depuis_champs({"gamma": "18", "phi": "30", "type_poussee": "au_repos"})
    assert s.type_poussee is TypePoussee.AU_REPOS


def test_sol_depuis_champs_ks_en_mpa_par_m():
    s = sol_depuis_champs({"gamma": "18", "phi": "30", "ks": "30"})
    assert s.ks == pytest.approx(MPa(30))


def test_materiaux_depuis_champs():
    m = materiaux_depuis_champs({"classe_beton": "C30/37", "enrobage_terre": "50", "enrobage_interieur": "40"})
    assert en_MPa(m.beton.fck) == pytest.approx(30.0)
    assert m.enrobage_terre == pytest.approx(0.05)
    assert m.enrobage_interieur == pytest.approx(0.04)


def test_materiaux_depuis_champs_classe_manquante_leve_une_erreur():
    with pytest.raises(ValueError, match="Classe de béton"):
        materiaux_depuis_champs({"enrobage_terre": "50", "enrobage_interieur": "40"})


def test_materiaux_depuis_champs_classe_inconnue_propage_l_erreur():
    with pytest.raises(ValueError):
        materiaux_depuis_champs({"classe_beton": "C99/99", "enrobage_terre": "50", "enrobage_interieur": "40"})


def test_appuis_depuis_champs_defauts():
    a = appuis_depuis_champs({})
    assert a.pied is TypeAppuiPied.ENCASTREMENT
    assert a.tete is TypeAppuiTete.LIBRE
    assert a.k_theta is None


def test_appuis_depuis_champs_ressort_et_tete_appuyee():
    a = appuis_depuis_champs({"pied": "ressort", "tete": "appui_dalle", "k_theta": "10"})
    assert a.pied is TypeAppuiPied.RESSORT
    assert a.tete is TypeAppuiTete.APPUI_DALLE
    assert a.k_theta == pytest.approx(MPa(10))


def test_charge_depuis_champs_charge_tete():
    c = charge_depuis_champs(
        {"nom": "Charge tête", "type": "charge_tete", "categorie": "Q", "valeur": "30", "psi0": "0.7",
         "psi1": "0.5", "psi2": "0.3", "excentricite": "0.05"}
    )
    assert c.type is TypeCharge.CHARGE_TETE
    assert c.categorie is CategorieAction.Q
    assert en_kN(c.valeur) == pytest.approx(30.0)
    assert c.psi0 == pytest.approx(0.7)
    assert c.parametres["excentricite"] == pytest.approx(0.05)


def test_charge_depuis_champs_poids_propre_ignore_la_valeur():
    c = charge_depuis_champs({"nom": "Poids propre", "type": "poids_propre", "categorie": "G"})
    assert c.valeur == 0.0


def test_charge_depuis_champs_compactage_en_kn_m2():
    c = charge_depuis_champs(
        {"nom": "Compactage", "type": "pression_compactage", "categorie": "Q", "valeur": "10",
         "profondeur_application": "1.5"}
    )
    assert en_kN_m2(c.valeur) == pytest.approx(10.0)
    assert c.parametres["profondeur_application"] == pytest.approx(1.5)


def test_charge_depuis_champs_type_inconnu_leve_une_erreur():
    with pytest.raises(ValueError, match="Type de charge"):
        charge_depuis_champs({"nom": "X", "type": "inconnu", "categorie": "G", "valeur": "1"})


def test_charge_depuis_champs_categorie_inconnue_leve_une_erreur():
    with pytest.raises(ValueError, match="Catégorie"):
        charge_depuis_champs({"nom": "X", "type": "charge_tete", "categorie": "Z", "valeur": "1"})


def test_charge_depuis_champs_nom_manquant_leve_une_erreur():
    with pytest.raises(ValueError, match="Nom"):
        charge_depuis_champs({"type": "charge_tete", "categorie": "Q", "valeur": "1"})


def test_champs_depuis_charge_aller_retour_charge_tete():
    original = charge_depuis_champs(
        {"nom": "Charge tête", "type": "charge_tete", "categorie": "Q", "valeur": "30", "psi0": "0.7",
         "psi1": "0.5", "psi2": "0.3", "excentricite": "0.05"}
    )
    champs = champs_depuis_charge(original)
    assert champs["nom"] == "Charge tête"
    assert champs["type"] == "charge_tete"
    assert champs["categorie"] == "Q"
    assert champs["valeur"] == "30"
    assert champs["psi0"] == "0.7"
    assert champs["excentricite"] == "0.05"
    assert champs["distance"] == ""

    reconstruite = charge_depuis_champs(champs)
    assert reconstruite.valeur == pytest.approx(original.valeur)
    assert reconstruite.type is original.type
    assert reconstruite.parametres == original.parametres


def test_champs_depuis_charge_poids_propre_valeur_nulle():
    original = charge_depuis_champs({"nom": "Poids propre", "type": "poids_propre", "categorie": "G"})
    champs = champs_depuis_charge(original)
    assert champs["valeur"] == "0"


def test_champs_depuis_charge_compactage_en_kn_m2():
    original = charge_depuis_champs(
        {"nom": "Compactage", "type": "pression_compactage", "categorie": "Q", "valeur": "10",
         "profondeur_application": "1.5"}
    )
    champs = champs_depuis_charge(original)
    assert champs["valeur"] == "10"
    assert champs["profondeur_application"] == "1.5"
