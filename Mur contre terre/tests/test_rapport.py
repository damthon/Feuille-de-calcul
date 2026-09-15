from mur_contre_terre.calcul import calculer
from mur_contre_terre.donnees.appuis import ConditionsAppui, TypeAppuiPied, TypeAppuiTete
from mur_contre_terre.donnees.charges import CasDeCharge, CategorieAction, TypeCharge
from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.donnees.materiaux import Acier, Beton, Materiaux
from mur_contre_terre.donnees.projet import Projet
from mur_contre_terre.donnees.sol import Sol, TypePoussee
from mur_contre_terre.rapport import generer_note_calcul
from mur_contre_terre.unites import deg, kN, kN_m3


def _projet() -> Projet:
    return Projet(
        nom="Mur de sous-sol — test",
        geometrie=Geometrie(hauteur=3.0, ep_base=0.30, ep_couronnement=0.20, debord_semelle=0.8, ep_semelle=0.4),
        sol=Sol(gamma=kN_m3(18), phi=deg(30), delta=deg(20), type_poussee=TypePoussee.ACTIF),
        appuis=ConditionsAppui(pied=TypeAppuiPied.ENCASTREMENT, tete=TypeAppuiTete.LIBRE),
        materiaux=Materiaux(
            beton=Beton.depuis_classe("C30/37"), acier=Acier.b500b(), enrobage_terre=0.05, enrobage_interieur=0.04
        ),
        charges=(
            CasDeCharge(nom="Poids propre", type=TypeCharge.POIDS_PROPRE, categorie=CategorieAction.G, valeur=0.0),
            CasDeCharge(nom="Poussee", type=TypeCharge.POUSSEE_TERRES, categorie=CategorieAction.G, valeur=0.0),
            CasDeCharge(
                nom="Charge tete", type=TypeCharge.CHARGE_TETE, categorie=CategorieAction.Q, valeur=kN(30),
                psi0=0.7, psi1=0.5, psi2=0.3,
            ),
        ),
        finesse_maillage=0.5,
    )


def test_generer_note_calcul_contient_le_nom_du_projet():
    projet = _projet()
    md = generer_note_calcul(projet, calculer(projet))
    assert "Mur de sous-sol — test" in md


def test_generer_note_calcul_contient_une_ligne_par_element():
    projet = _projet()
    resultat = calculer(projet)
    md = generer_note_calcul(projet, resultat)
    for v in resultat.verifications:
        assert f"{v.position:.2f}" in md


def test_generer_note_calcul_cite_les_clauses_sia():
    projet = _projet()
    md = generer_note_calcul(projet, calculer(projet))
    for clause in ("SIA 261 §4.3.2", "SIA 262 §4.1", "SIA 260 §4.4.3.2", "SIA 262 §4.3.3"):
        assert clause in md


def test_generer_note_calcul_avertit_sur_l_effort_tranchant_non_confirme():
    projet = _projet()
    md = generer_note_calcul(projet, calculer(projet))
    assert "à confirmer" in md
