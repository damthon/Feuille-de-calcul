import math

import pytest

from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.mecanique.maillage import Maillage, generer_maillage


def test_generer_maillage_respecte_la_finesse():
    g = Geometrie(hauteur=3.0, ep_base=0.30, ep_couronnement=0.20, debord_semelle=0.8, ep_semelle=0.4)
    m = generer_maillage(g, finesse=0.4)
    assert m.positions[0] == 0.0
    assert m.positions[-1] == pytest.approx(3.0)
    assert all(m.longueur_element(i) <= 0.4 + 1e-9 for i in range(m.nb_elements))
    assert m.nb_noeuds == m.nb_elements + 1


def test_generer_maillage_un_seul_element_si_finesse_large():
    g = Geometrie(hauteur=3.0, ep_base=0.30, ep_couronnement=0.20, debord_semelle=0.8, ep_semelle=0.4)
    m = generer_maillage(g, finesse=10.0)
    assert m.nb_elements == 1


def test_generer_maillage_finesse_non_positive_leve_une_erreur():
    g = Geometrie(hauteur=3.0, ep_base=0.30, ep_couronnement=0.20, debord_semelle=0.8, ep_semelle=0.4)
    with pytest.raises(ValueError):
        generer_maillage(g, finesse=0.0)


def test_maillage_positions_non_croissantes_leve_une_erreur():
    with pytest.raises(ValueError):
        Maillage((0.0, 1.0, 0.5, 2.0))


def test_maillage_moins_de_deux_noeuds_leve_une_erreur():
    with pytest.raises(ValueError):
        Maillage((0.0,))


def test_dofs_element_sont_contigus():
    m = Maillage((0.0, 1.0, 2.0, 3.0))
    assert list(m.dofs_element(0)) == [0, 1, 2, 3, 4, 5]
    assert list(m.dofs_element(1)) == [3, 4, 5, 6, 7, 8]
    assert list(m.dofs_element(2)) == [6, 7, 8, 9, 10, 11]
    assert m.nb_dof == 12


def test_milieu_element():
    m = Maillage((0.0, 1.0, 3.0))
    assert m.milieu_element(0) == pytest.approx(0.5)
    assert m.milieu_element(1) == pytest.approx(2.0)
