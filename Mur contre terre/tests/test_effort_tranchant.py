import math

import pytest

from mur_contre_terre.donnees.materiaux import Beton
from mur_contre_terre.section_ba.effort_tranchant import (
    C_RD_C,
    K1,
    TAUX_ARMATURE_MAX,
    V_MIN_COEF,
    coefficient_taille,
    resistance_effort_tranchant,
    taux_armature_longitudinale,
)
from mur_contre_terre.section_ba.modele_beton import GAMMA_C


def _beton() -> Beton:
    return Beton.depuis_classe("C30/37")


def test_coefficient_taille_plafonne_a_deux():
    assert coefficient_taille(0.15) == pytest.approx(2.0)
    assert coefficient_taille(0.2) == pytest.approx(2.0)


def test_coefficient_taille_formule():
    d = 0.4
    assert coefficient_taille(d) == pytest.approx(1.0 + math.sqrt(0.2 / d))


def test_coefficient_taille_non_positif_leve_une_erreur():
    with pytest.raises(ValueError):
        coefficient_taille(0.0)


def test_taux_armature_longitudinale_formule():
    assert taux_armature_longitudinale(8e-4, 1.0, 0.25) == pytest.approx(8e-4 / 0.25)


def test_taux_armature_longitudinale_negative_leve_une_erreur():
    with pytest.raises(ValueError):
        taux_armature_longitudinale(-1e-4, 1.0, 0.25)


def test_resistance_effort_tranchant_formule_de_reference():
    beton = _beton()
    b, d, rho = 1.0, 0.25, 0.0032
    k = coefficient_taille(d)
    fck_mpa = beton.fck / 1e6
    c_rd_c = C_RD_C / GAMMA_C
    v_rd_mpa = c_rd_c * k * (100.0 * rho * fck_mpa) ** (1.0 / 3.0)
    v_min_mpa = V_MIN_COEF * k**1.5 * math.sqrt(fck_mpa)
    attendu = max(v_rd_mpa, v_min_mpa) * 1e6 * b * d
    assert resistance_effort_tranchant(beton, b, d, rho) == pytest.approx(attendu, rel=1e-9)


def test_resistance_effort_tranchant_croit_avec_le_taux_armature():
    beton = _beton()
    v_faible = resistance_effort_tranchant(beton, 1.0, 0.25, 0.002)
    v_fort = resistance_effort_tranchant(beton, 1.0, 0.25, 0.015)
    assert v_fort > v_faible


def test_resistance_effort_tranchant_compression_favorable():
    beton = _beton()
    sans_n = resistance_effort_tranchant(beton, 1.0, 0.25, 0.003)
    avec_compression = resistance_effort_tranchant(beton, 1.0, 0.25, 0.003, effort_normal=-200e3)
    assert avec_compression > sans_n


def test_resistance_effort_tranchant_traction_est_ignoree_pas_defavorable():
    beton = _beton()
    sans_n = resistance_effort_tranchant(beton, 1.0, 0.25, 0.003)
    avec_traction = resistance_effort_tranchant(beton, 1.0, 0.25, 0.003, effort_normal=200e3)
    assert avec_traction == pytest.approx(sans_n)


def test_resistance_effort_tranchant_sigma_cp_plafonnee():
    beton = _beton()
    # compression énorme : sigma_cp doit être plafonnée à 0.2*fcd, pas croître indéfiniment
    v_grande_compression = resistance_effort_tranchant(beton, 1.0, 0.25, 0.003, effort_normal=-50e6)
    v_plafond = resistance_effort_tranchant(beton, 1.0, 0.25, 0.003, effort_normal=-5e6)
    assert v_grande_compression == pytest.approx(v_plafond, rel=1e-6)


def test_resistance_effort_tranchant_taux_armature_plafonne():
    beton = _beton()
    v_a_la_limite = resistance_effort_tranchant(beton, 1.0, 0.25, TAUX_ARMATURE_MAX)
    v_au_dela = resistance_effort_tranchant(beton, 1.0, 0.25, TAUX_ARMATURE_MAX * 2.0)
    assert v_au_dela == pytest.approx(v_a_la_limite, rel=1e-9)


def test_resistance_effort_tranchant_geometrie_non_positive_leve_une_erreur():
    with pytest.raises(ValueError):
        resistance_effort_tranchant(_beton(), 0.0, 0.25, 0.003)
    with pytest.raises(ValueError):
        resistance_effort_tranchant(_beton(), 1.0, 0.0, 0.003)


def test_resistance_effort_tranchant_taux_negatif_leve_une_erreur():
    with pytest.raises(ValueError):
        resistance_effort_tranchant(_beton(), 1.0, 0.25, -0.001)
