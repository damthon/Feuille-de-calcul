import pytest

from mur_contre_terre.donnees.charges import CasDeCharge, CategorieAction, TypeCharge
from mur_contre_terre.unites import kN


def test_charge_avec_parametres():
    c = CasDeCharge(
        nom="Charge en tête",
        type=TypeCharge.CHARGE_TETE,
        categorie=CategorieAction.G,
        valeur=kN(80),
        psi0=0.7,
        parametres={"excentricite": 0.05},
    )
    assert c.parametres["excentricite"] == 0.05


def test_parametres_est_immuable():
    c = CasDeCharge(nom="x", type=TypeCharge.SURCHARGE_TETE, categorie=CategorieAction.Q, valeur=kN(10))
    with pytest.raises(TypeError):
        c.parametres["y"] = 1.0


def test_psi_hors_domaine_leve_une_erreur():
    with pytest.raises(ValueError):
        CasDeCharge(nom="x", type=TypeCharge.SURCHARGE_TETE, categorie=CategorieAction.Q, valeur=kN(10), psi0=1.5)
