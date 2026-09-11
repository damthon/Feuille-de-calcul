import numpy as np
import pytest

from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.donnees.materiaux import Acier, Beton, Materiaux
from mur_contre_terre.mecanique.maillage import Maillage
from mur_contre_terre.mecanique.rigidite import assembler, k_element, rigidites_par_element


def test_k_element_est_symetrique():
    k = k_element(ea=1e9, ei=5000.0, longueur=1.5)
    assert k.shape == (6, 6)
    assert np.allclose(k, k.T)


def test_k_element_longueur_non_positive_leve_une_erreur():
    with pytest.raises(ValueError):
        k_element(ea=1e9, ei=5000.0, longueur=0.0)


def test_k_element_blocs_axial_et_flexion_decouples():
    k = k_element(ea=100.0, ei=200.0, longueur=2.0)
    # Le bloc axial (indices 0,3) ne doit influencer aucun DOF de flexion (1,2,4,5)
    for i in (0, 3):
        for j in (1, 2, 4, 5):
            assert k[i, j] == 0.0
            assert k[j, i] == 0.0


def test_rigidites_par_element_mur_prismatique():
    g = Geometrie(hauteur=3.0, ep_base=0.30, ep_couronnement=0.30, debord_semelle=0.8, ep_semelle=0.4)
    mat = Materiaux(beton=Beton.depuis_classe("C30/37"), acier=Acier.b500b(), enrobage_terre=0.05, enrobage_interieur=0.04)
    m = Maillage((0.0, 1.0, 2.0, 3.0))
    ea, ei = rigidites_par_element(g, mat, m)
    assert len(ea) == len(ei) == 3
    # section constante (ep_base == ep_couronnement) => EA, EI identiques sur tous les éléments
    assert ea[0] == pytest.approx(ea[1]) == pytest.approx(ea[2])
    assert ei[0] == pytest.approx(ei[1]) == pytest.approx(ei[2])
    aire_attendue = 0.30 * 1.0
    assert ea[0] == pytest.approx(mat.beton.Ecm * aire_attendue)


def test_rigidites_par_element_mur_effile_decroit_vers_la_tete():
    g = Geometrie(hauteur=3.0, ep_base=0.40, ep_couronnement=0.20, debord_semelle=0.8, ep_semelle=0.4)
    mat = Materiaux(beton=Beton.depuis_classe("C30/37"), acier=Acier.b500b(), enrobage_terre=0.05, enrobage_interieur=0.04)
    m = Maillage((0.0, 1.0, 2.0, 3.0))
    ea, ei = rigidites_par_element(g, mat, m)
    assert ea[0] > ea[1] > ea[2]
    assert ei[0] > ei[1] > ei[2]


def test_assembler_dimension_et_symetrie():
    m = Maillage((0.0, 1.0, 2.0))
    ea = [1e9, 1e9]
    ei = [5000.0, 5000.0]
    K = assembler(m, ea, ei)
    assert K.shape == (9, 9)
    assert np.allclose(K, K.T)


def test_assembler_nombre_incorrect_de_rigidites_leve_une_erreur():
    m = Maillage((0.0, 1.0, 2.0))
    with pytest.raises(ValueError):
        assembler(m, ea=[1e9], ei=[5000.0, 5000.0])
