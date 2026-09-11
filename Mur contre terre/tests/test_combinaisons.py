import numpy as np
import pytest

from mur_contre_terre.donnees.charges import CasDeCharge, CategorieAction, TypeCharge
from mur_contre_terre.mecanique.combinaisons import (
    Combinaison,
    generer_combinaisons_elu,
    generer_combinaisons_els,
    vecteur_combine,
)


def _g(nom, valeur=100.0):
    return CasDeCharge(nom=nom, type=TypeCharge.POIDS_PROPRE, categorie=CategorieAction.G, valeur=valeur)


def _q(nom, valeur=50.0, psi0=0.7, psi1=0.5, psi2=0.3):
    return CasDeCharge(
        nom=nom, type=TypeCharge.SURCHARGE_TETE, categorie=CategorieAction.Q, valeur=valeur,
        psi0=psi0, psi1=psi1, psi2=psi2,
    )


def test_elu_sans_action_variable_une_seule_combinaison():
    charges = [_g("G1"), _g("G2")]
    combinaisons = generer_combinaisons_elu(charges)
    assert len(combinaisons) == 1
    assert combinaisons[0].facteurs == {"G1": 1.35, "G2": 1.35}


def test_elu_deux_actions_variables_une_combinaison_par_dominante():
    charges = [_g("G1"), _q("Q1", psi0=0.7), _q("Q2", psi0=0.6)]
    combinaisons = generer_combinaisons_elu(charges)
    assert len(combinaisons) == 2

    noms = {c.nom for c in combinaisons}
    assert any("Q1 dominante" in n for n in noms)
    assert any("Q2 dominante" in n for n in noms)

    q1_dominante = next(c for c in combinaisons if "Q1 dominante" in c.nom)
    assert q1_dominante.facteurs["G1"] == pytest.approx(1.35)
    assert q1_dominante.facteurs["Q1"] == pytest.approx(1.5)
    assert q1_dominante.facteurs["Q2"] == pytest.approx(1.5 * 0.6)


def test_elu_facteurs_personnalises():
    charges = [_g("G1"), _q("Q1")]
    combinaisons = generer_combinaisons_elu(charges, gamma_g=1.2, gamma_q=1.4)
    assert combinaisons[0].facteurs["G1"] == pytest.approx(1.2)
    assert combinaisons[0].facteurs["Q1"] == pytest.approx(1.4)


def test_els_sans_action_variable():
    charges = [_g("G1")]
    combinaisons = generer_combinaisons_els(charges)
    assert len(combinaisons) == 1
    assert combinaisons[0].facteurs == {"G1": 1.0}


def test_els_deux_actions_variables_utilise_psi1_et_psi2():
    charges = [_g("G1"), _q("Q1", psi1=0.5, psi2=0.3), _q("Q2", psi1=0.6, psi2=0.4)]
    combinaisons = generer_combinaisons_els(charges)
    q1_dominante = next(c for c in combinaisons if "Q1 dominante" in c.nom)
    assert q1_dominante.facteurs["G1"] == pytest.approx(1.0)
    assert q1_dominante.facteurs["Q1"] == pytest.approx(0.5)  # psi1 de Q1
    assert q1_dominante.facteurs["Q2"] == pytest.approx(0.4)  # psi2 de Q2


def test_combinaison_facteurs_est_immuable():
    c = Combinaison("test", {"A": 1.0})
    with pytest.raises(TypeError):
        c.facteurs["B"] = 2.0


def test_vecteur_combine_somme_ponderee():
    combinaison = Combinaison("test", {"A": 1.35, "B": 1.5})
    vecteurs = {"A": np.array([1.0, 2.0]), "B": np.array([10.0, 0.0])}
    resultat = vecteur_combine(combinaison, vecteurs)
    assert np.allclose(resultat, [1.35 * 1.0 + 1.5 * 10.0, 1.35 * 2.0 + 1.5 * 0.0])


def test_vecteur_combine_cle_manquante_leve_une_erreur():
    combinaison = Combinaison("test", {"A": 1.0})
    with pytest.raises(KeyError):
        vecteur_combine(combinaison, {})
