import math

from mur_contre_terre.unites import (
    MPa, deg, en_deg, en_kN, en_kN_m2, en_kN_m3, en_kNm, en_MPa, kN, kNm, kN_m2, kN_m3,
)


def test_forces():
    assert kN(850) == 850e3
    assert en_kN(850e3) == 850.0


def test_moments():
    assert kNm(120) == 120e3
    assert en_kNm(120e3) == 120.0


def test_contraintes():
    assert MPa(30) == 30e6
    assert en_MPa(30e6) == 30.0
    assert kN_m2(18) == 18e3
    assert en_kN_m2(18e3) == 18.0


def test_poids_volumique():
    assert kN_m3(18) == 18e3
    assert en_kN_m3(18e3) == 18.0


def test_angles():
    assert math.isclose(deg(30), math.pi / 6)
    assert math.isclose(en_deg(math.pi / 6), 30.0)
