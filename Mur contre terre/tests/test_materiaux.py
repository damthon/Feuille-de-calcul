import math

import pytest

from mur_contre_terre.donnees.materiaux import Acier, Beton, Materiaux
from mur_contre_terre.unites import MPa


def test_beton_depuis_classe():
    b = Beton.depuis_classe("C30/37")
    assert math.isclose(b.fck, MPa(30))
    assert math.isclose(b.fctm, MPa(2.9))
    assert math.isclose(b.Ecm, MPa(33000))


def test_classe_inconnue_leve_une_erreur():
    with pytest.raises(ValueError):
        Beton.depuis_classe("C99/99")


def test_beton_poids_volumique_par_defaut():
    b = Beton.depuis_classe("C30/37")
    assert math.isclose(b.poids_volumique, 25.0e3)


def test_beton_poids_volumique_non_positif_leve_une_erreur():
    with pytest.raises(ValueError):
        Beton(fck=MPa(30), fctm=MPa(2.9), Ecm=MPa(33000), poids_volumique=0.0)


def test_acier_b500b():
    a = Acier.b500b()
    assert math.isclose(a.fsk, MPa(500))
    assert math.isclose(a.Es, 205e9)


def test_materiaux_enrobage_non_positif_leve_une_erreur():
    with pytest.raises(ValueError):
        Materiaux(beton=Beton.depuis_classe("C30/37"), acier=Acier.b500b(), enrobage_terre=0.0, enrobage_interieur=0.04)


def test_acier_k_durcissement_par_defaut():
    assert math.isclose(Acier.b500b().k_durcissement, 1.08)


def test_acier_k_durcissement_non_superieur_a_un_leve_une_erreur():
    with pytest.raises(ValueError):
        Acier(k_durcissement=1.0)
