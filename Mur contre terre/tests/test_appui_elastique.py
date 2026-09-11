import pytest

from mur_contre_terre.geotechnique.appui_elastique import rigidite_rotation, semelle_entierement_comprimee


def test_rigidite_rotation():
    ks = 30e6  # N/m³
    b = 1.5  # m
    assert rigidite_rotation(ks, b) == pytest.approx(ks * b**3 / 12.0)


def test_rigidite_rotation_valeurs_non_positives_levent_une_erreur():
    with pytest.raises(ValueError):
        rigidite_rotation(0.0, 1.5)
    with pytest.raises(ValueError):
        rigidite_rotation(30e6, 0.0)


def test_semelle_comprimee_excentricite_dans_le_noyau():
    # N=200kN, M=20kNm, B=1.5m -> e=0.10m <= B/6=0.25m
    assert semelle_entierement_comprimee(n=200e3, moment=20e3, largeur_semelle=1.5) is True


def test_semelle_non_comprimee_excentricite_hors_noyau():
    # N=200kN, M=60kNm, B=1.5m -> e=0.30m > B/6=0.25m
    assert semelle_entierement_comprimee(n=200e3, moment=60e3, largeur_semelle=1.5) is False


def test_semelle_traction_nette_non_comprimee():
    assert semelle_entierement_comprimee(n=0.0, moment=10e3, largeur_semelle=1.5) is False
