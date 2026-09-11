import pytest

from mur_contre_terre.geotechnique.compactage import pression_compactage


def test_constante_dans_la_zone_d_application():
    assert pression_compactage(intensite=8e3, profondeur_application=2.0, profondeur=0.0) == 8e3
    assert pression_compactage(intensite=8e3, profondeur_application=2.0, profondeur=2.0) == 8e3


def test_nulle_au_dela():
    assert pression_compactage(intensite=8e3, profondeur_application=2.0, profondeur=2.5) == 0.0


def test_profondeur_negative_leve_une_erreur():
    with pytest.raises(ValueError):
        pression_compactage(intensite=8e3, profondeur_application=2.0, profondeur=-0.1)
