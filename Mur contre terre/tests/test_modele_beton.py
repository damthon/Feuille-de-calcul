import pytest

from mur_contre_terre.donnees.materiaux import Beton
from mur_contre_terre.section_ba.modele_beton import (
    EPS_C2,
    GAMMA_C,
    contrainte_beton,
    deformation_fissuration,
    fcd,
)


def _beton() -> Beton:
    return Beton.depuis_classe("C30/37")


def test_fcd_est_fck_sur_gamma_c():
    b = _beton()
    assert fcd(b) == pytest.approx(b.fck / GAMMA_C)


def test_contrainte_nulle_a_deformation_nulle():
    assert contrainte_beton(0.0, _beton()) == pytest.approx(0.0)


def test_compression_au_pic_de_la_parabole_vaut_fcd():
    b = _beton()
    assert contrainte_beton(-EPS_C2, b) == pytest.approx(-fcd(b), rel=1e-9)


def test_compression_sur_le_plateau_vaut_fcd():
    b = _beton()
    assert contrainte_beton(-b.epsilon_cu, b) == pytest.approx(-fcd(b), rel=1e-9)
    # tout le plateau (entre eps_c2 et epsilon_cu) reste à fcd
    assert contrainte_beton(-(EPS_C2 + b.epsilon_cu) / 2.0, b) == pytest.approx(-fcd(b), rel=1e-9)


def test_compression_au_dela_de_epsilon_cu_est_tronquee():
    b = _beton()
    assert contrainte_beton(-2.0 * b.epsilon_cu, b) == pytest.approx(-fcd(b), rel=1e-9)


def test_compression_utilise_fck_hors_calcul_elu():
    b = _beton()
    assert contrainte_beton(-b.epsilon_cu, b, calcul=False) == pytest.approx(-b.fck, rel=1e-9)


def test_compression_intermediaire_suit_la_parabole():
    b = _beton()
    eps = EPS_C2 / 2.0
    attendu = -fcd(b) * (1.0 - (1.0 - eps / EPS_C2) ** 2)
    assert contrainte_beton(-eps, b) == pytest.approx(attendu, rel=1e-9)


def test_traction_elastique_jusqu_a_fissuration():
    b = _beton()
    eps = deformation_fissuration(b) / 2.0
    assert contrainte_beton(eps, b) == pytest.approx(b.Ecm * eps, rel=1e-9)


def test_traction_nulle_au_dela_de_fissuration():
    b = _beton()
    eps = deformation_fissuration(b) * 1.5
    assert contrainte_beton(eps, b) == pytest.approx(0.0)


def test_deformation_fissuration_est_fctm_sur_ecm():
    b = _beton()
    assert deformation_fissuration(b) == pytest.approx(b.fctm / b.Ecm)


def test_contrainte_beton_continue_a_la_fissuration():
    b = _beton()
    eps_fiss = deformation_fissuration(b)
    avant = contrainte_beton(eps_fiss * 0.999999, b)
    assert avant == pytest.approx(b.fctm, rel=1e-4)
