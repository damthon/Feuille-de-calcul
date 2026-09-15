import pytest

from mur_contre_terre.donnees.materiaux import Acier, Beton, Materiaux
from mur_contre_terre.section_ba.flexion_composee import SectionRectangulaire
from mur_contre_terre.section_ba.moment_courbure import (
    courbe_moment_courbure,
    courbure_ultime,
    rigidite_non_fissuree,
    rigidite_secante,
)


def _materiaux() -> Materiaux:
    return Materiaux(
        beton=Beton.depuis_classe("C30/37"), acier=Acier.b500b(), enrobage_terre=0.05, enrobage_interieur=0.04
    )


def _section() -> SectionRectangulaire:
    return SectionRectangulaire(epaisseur=0.30, enrobage_terre=0.05, enrobage_interieur=0.04)


_AS_TERRE = 4e-4
_AS_INTERIEUR = 8e-4


def test_rigidite_non_fissuree_formule():
    section, materiaux = _section(), _materiaux()
    attendu = materiaux.beton.Ecm * section.largeur * section.epaisseur**3 / 12.0
    assert rigidite_non_fissuree(section, materiaux) == pytest.approx(attendu)


def test_courbure_ultime_positive_pour_sens_positif():
    chi_u = courbure_ultime(0.0, _section(), _materiaux(), _AS_TERRE, _AS_INTERIEUR, sens=1)
    assert chi_u > 0.0


def test_courbure_ultime_negative_pour_sens_negatif():
    chi_u = courbure_ultime(0.0, _section(), _materiaux(), _AS_TERRE, _AS_INTERIEUR, sens=-1)
    assert chi_u < 0.0


def test_courbure_ultime_sens_invalide_leve_une_erreur():
    with pytest.raises(ValueError):
        courbure_ultime(0.0, _section(), _materiaux(), _AS_TERRE, _AS_INTERIEUR, sens=0)


def test_courbure_ultime_effort_normal_hors_capacite_leve_une_erreur():
    with pytest.raises(ValueError):
        courbure_ultime(5.0e6, _section(), _materiaux(), _AS_TERRE, _AS_INTERIEUR)


def test_courbe_moment_courbure_nb_points_et_courbure_croissante():
    section, materiaux = _section(), _materiaux()
    pts = courbe_moment_courbure(0.0, section, materiaux, _AS_TERRE, _AS_INTERIEUR, sens=1, nb_paliers=10)
    assert len(pts) == 10
    chis = [p.chi for p in pts]
    assert chis == sorted(chis)
    assert chis[0] > 0.0


def test_courbe_moment_courbure_moment_croissant_en_valeur_absolue():
    section, materiaux = _section(), _materiaux()
    pts = courbe_moment_courbure(0.0, section, materiaux, _AS_TERRE, _AS_INTERIEUR, sens=1, nb_paliers=10)
    moments = [p.m for p in pts]
    assert all(m > 0.0 for m in moments)
    assert moments[-1] > moments[0]


def test_courbe_moment_courbure_rigidite_secante_diminue_avec_la_fissuration():
    section, materiaux = _section(), _materiaux()
    pts = courbe_moment_courbure(0.0, section, materiaux, _AS_TERRE, _AS_INTERIEUR, sens=1, nb_paliers=10)
    ei = [p.ei_secant for p in pts]
    assert ei[0] > ei[-1]
    assert ei[0] <= rigidite_non_fissuree(section, materiaux)


def test_courbe_moment_courbure_sens_negatif_donne_un_moment_negatif():
    section, materiaux = _section(), _materiaux()
    pts = courbe_moment_courbure(0.0, section, materiaux, _AS_TERRE, _AS_INTERIEUR, sens=-1, nb_paliers=5)
    assert all(p.m < 0.0 for p in pts)
    assert all(p.chi < 0.0 for p in pts)


def test_courbe_moment_courbure_dernier_palier_est_la_courbure_ultime():
    section, materiaux = _section(), _materiaux()
    chi_u = courbure_ultime(0.0, section, materiaux, _AS_TERRE, _AS_INTERIEUR, sens=1)
    pts = courbe_moment_courbure(0.0, section, materiaux, _AS_TERRE, _AS_INTERIEUR, sens=1, nb_paliers=20)
    assert pts[-1].chi == pytest.approx(chi_u, rel=1e-6)


def test_courbe_moment_courbure_nb_paliers_non_positif_leve_une_erreur():
    with pytest.raises(ValueError):
        courbe_moment_courbure(0.0, _section(), _materiaux(), _AS_TERRE, _AS_INTERIEUR, nb_paliers=0)


def test_rigidite_secante_moment_nul_donne_la_rigidite_non_fissuree():
    section, materiaux = _section(), _materiaux()
    assert rigidite_secante(0.0, 0.0, section, materiaux, _AS_TERRE, _AS_INTERIEUR) == pytest.approx(
        rigidite_non_fissuree(section, materiaux)
    )


def test_rigidite_secante_coherente_avec_la_courbe_directe():
    # Le tout premier palier (juste après l'amorce de fissuration) est exclu : l'intégration
    # par fibres y discrétise la coupure de traction du béton en petits paliers non strictement
    # monotones (voir modele_beton.py), si bien que la bissection sur chi peut y converger sur
    # une racine proche mais distincte de celle de courbe_moment_courbure. Les paliers suivants,
    # eux, coïncident à la précision machine.
    section, materiaux = _section(), _materiaux()
    pts = courbe_moment_courbure(0.0, section, materiaux, _AS_TERRE, _AS_INTERIEUR, sens=1, nb_paliers=8)
    for p in pts[1:]:
        ei = rigidite_secante(p.m, 0.0, section, materiaux, _AS_TERRE, _AS_INTERIEUR)
        assert ei == pytest.approx(p.ei_secant, rel=1e-6)


def test_rigidite_secante_moment_hors_capacite_leve_une_erreur():
    with pytest.raises(ValueError):
        rigidite_secante(1.0e9, 0.0, _section(), _materiaux(), _AS_TERRE, _AS_INTERIEUR)
