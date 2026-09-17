import matplotlib

matplotlib.use("Agg")

from mur_contre_terre.calcul import calculer
from mur_contre_terre.donnees.appuis import ConditionsAppui, TypeAppuiPied, TypeAppuiTete
from mur_contre_terre.donnees.charges import CasDeCharge, CategorieAction, TypeCharge
from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.donnees.materiaux import Acier, Beton, Materiaux
from mur_contre_terre.donnees.projet import Projet
from mur_contre_terre.donnees.sol import Sol, TypePoussee
from mur_contre_terre.section_ba.flexion_composee import SectionRectangulaire
from mur_contre_terre.section_ba.moment_courbure import courbe_moment_courbure
from mur_contre_terre.trace import (
    figure_charges,
    figure_deformee,
    figure_diagramme,
    figure_efforts,
    figure_geometrie,
    figure_moment_courbure,
    figure_section_materiaux,
)
from mur_contre_terre.unites import deg, kN, kN_m2, kN_m3


def _projet() -> Projet:
    return Projet(
        nom="Test",
        geometrie=Geometrie(hauteur=3.0, ep_base=0.30, ep_couronnement=0.20, debord_semelle=0.8, ep_semelle=0.4),
        sol=Sol(gamma=kN_m3(18), phi=deg(30), delta=deg(20), type_poussee=TypePoussee.ACTIF),
        appuis=ConditionsAppui(pied=TypeAppuiPied.ENCASTREMENT, tete=TypeAppuiTete.LIBRE),
        materiaux=Materiaux(
            beton=Beton.depuis_classe("C30/37"), acier=Acier.b500b(), enrobage_terre=0.05, enrobage_interieur=0.04
        ),
        charges=(
            CasDeCharge(nom="Poids propre", type=TypeCharge.POIDS_PROPRE, categorie=CategorieAction.G, valeur=0.0),
            CasDeCharge(nom="Poussee", type=TypeCharge.POUSSEE_TERRES, categorie=CategorieAction.G, valeur=0.0),
        ),
        finesse_maillage=0.5,
    )


def test_figure_geometrie_a_les_bons_axes():
    fig = figure_geometrie(_projet().geometrie)
    assert len(fig.axes) == 1


def test_figure_geometrie_avec_sol_et_appuis_ne_leve_pas_d_erreur():
    projet = _projet()
    sol_avec_nappe = Sol(
        gamma=kN_m3(18), phi=deg(30), beta=deg(5), gamma_sat=kN_m3(20), niveau_nappe=1.2,
    )
    appuis_ressort = ConditionsAppui(pied=TypeAppuiPied.RESSORT, tete=TypeAppuiTete.APPUI_DALLE)
    fig = figure_geometrie(projet.geometrie, sol_avec_nappe, appuis_ressort)
    assert len(fig.axes) == 1


def test_figure_section_materiaux_a_un_axe():
    projet = _projet()
    fig = figure_section_materiaux(projet.geometrie, projet.materiaux)
    assert len(fig.axes) == 1


def test_figure_charges_sans_charges_ne_leve_pas_d_erreur():
    projet = _projet()
    fig = figure_charges(projet.geometrie, projet.sol, [])
    assert len(fig.axes) == 1


def test_figure_charges_avec_tous_les_types_et_previsualisation():
    projet = _projet()
    sol = Sol(gamma=kN_m3(18), phi=deg(30), gamma_sat=kN_m3(20), niveau_nappe=1.0)
    charges = [
        CasDeCharge(nom="Poids propre", type=TypeCharge.POIDS_PROPRE, categorie=CategorieAction.G, valeur=0.0),
        CasDeCharge(nom="Charge tête", type=TypeCharge.CHARGE_TETE, categorie=CategorieAction.Q, valeur=kN(30)),
        CasDeCharge(nom="Poussée", type=TypeCharge.POUSSEE_TERRES, categorie=CategorieAction.G, valeur=0.0),
        CasDeCharge(
            nom="Surcharge", type=TypeCharge.SURCHARGE_TETE, categorie=CategorieAction.Q, valeur=kN_m2(10),
            parametres={"distance": 0.2, "etendue": 1.5},
        ),
        CasDeCharge(
            nom="Terreplein", type=TypeCharge.CHARGE_SURFACIQUE_TERREPLEIN, categorie=CategorieAction.Q,
            valeur=kN_m2(5),
        ),
        CasDeCharge(
            nom="Linéaire", type=TypeCharge.CHARGE_LINEAIRE_TERREPLEIN, categorie=CategorieAction.Q, valeur=kN(12),
            parametres={"distance": 0.6},
        ),
        CasDeCharge(nom="Hydrostatique", type=TypeCharge.PRESSION_HYDROSTATIQUE, categorie=CategorieAction.G, valeur=0.0),
        CasDeCharge(
            nom="Compactage", type=TypeCharge.PRESSION_COMPACTAGE, categorie=CategorieAction.Q, valeur=kN_m2(5),
            parametres={"profondeur_application": 0.8},
        ),
    ]
    previsualisation = CasDeCharge(
        nom="Nouvelle", type=TypeCharge.SURCHARGE_TETE, categorie=CategorieAction.Q, valeur=kN_m2(8),
    )
    fig = figure_charges(projet.geometrie, sol, charges, previsualisation)
    assert len(fig.axes) == 1


def test_figure_charges_hydrostatique_sans_nappe_definie_ne_leve_pas_d_erreur():
    projet = _projet()
    charge = CasDeCharge(nom="Hydro", type=TypeCharge.PRESSION_HYDROSTATIQUE, categorie=CategorieAction.G, valeur=0.0)
    fig = figure_charges(projet.geometrie, projet.sol, [charge])
    assert len(fig.axes) == 1


def test_figure_efforts_a_trois_sous_graphiques():
    r = calculer(_projet())
    fig = figure_efforts(r.resultats_elu[0], "ELU test")
    assert len(fig.axes) == 3


def test_figure_deformee_ne_leve_pas_d_erreur():
    r = calculer(_projet())
    fig = figure_deformee(r.maillage, r.resultats_elu[0].deplacements, amplification=10.0)
    assert len(fig.axes) == 1


def test_figure_diagramme_generique():
    r = calculer(_projet())
    fig = figure_diagramme(r.maillage, r.resultats_elu[0].deplacements[:, 1], "u", "m")
    assert len(fig.axes) == 1


def test_figure_moment_courbure():
    projet = _projet()
    section = SectionRectangulaire(0.3, 0.05, 0.04)
    pts = courbe_moment_courbure(0.0, section, projet.materiaux, 6e-4, 6e-4, nb_paliers=5)
    fig = figure_moment_courbure(pts)
    assert len(fig.axes) == 1
