import math

import pytest

from mur_contre_terre.donnees.geometrie import Geometrie


def test_largeur_semelle():
    g = Geometrie(hauteur=3.0, ep_base=0.30, ep_couronnement=0.20, debord_semelle=0.80, ep_semelle=0.40)
    assert math.isclose(g.largeur_semelle, 1.10)


def test_epaisseur_interpolee():
    g = Geometrie(hauteur=4.0, ep_base=0.40, ep_couronnement=0.20, debord_semelle=1.0, ep_semelle=0.5)
    assert math.isclose(g.epaisseur(0.0), 0.40)
    assert math.isclose(g.epaisseur(4.0), 0.20)
    assert math.isclose(g.epaisseur(2.0), 0.30)


def test_epaisseur_hors_domaine_leve_une_erreur():
    g = Geometrie(hauteur=3.0, ep_base=0.30, ep_couronnement=0.20, debord_semelle=0.8, ep_semelle=0.4)
    with pytest.raises(ValueError):
        g.epaisseur(-0.1)
    with pytest.raises(ValueError):
        g.epaisseur(3.1)


@pytest.mark.parametrize("champ", ["hauteur", "ep_base", "ep_couronnement", "debord_semelle", "ep_semelle"])
def test_valeur_non_positive_leve_une_erreur(champ):
    valeurs = dict(hauteur=3.0, ep_base=0.30, ep_couronnement=0.20, debord_semelle=0.8, ep_semelle=0.4)
    valeurs[champ] = 0.0
    with pytest.raises(ValueError):
        Geometrie(**valeurs)


def test_geometrie_est_immuable():
    g = Geometrie(hauteur=3.0, ep_base=0.30, ep_couronnement=0.20, debord_semelle=0.8, ep_semelle=0.4)
    with pytest.raises(AttributeError):
        g.hauteur = 5.0
