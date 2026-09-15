import pytest

from mur_contre_terre.donnees.materiaux import Acier
from mur_contre_terre.section_ba.modele_acier import (
    GAMMA_S,
    contrainte_acier,
    deformation_elastique,
    fsd,
)


def test_fsd_est_fsk_sur_gamma_s():
    a = Acier.b500b()
    assert fsd(a) == pytest.approx(a.fsk / GAMMA_S)


def test_contrainte_nulle_a_deformation_nulle():
    assert contrainte_acier(0.0, Acier.b500b()) == pytest.approx(0.0)


def test_palier_elastique_en_traction():
    a = Acier.b500b()
    eps = deformation_elastique(a) / 2.0
    assert contrainte_acier(eps, a) == pytest.approx(a.Es * eps, rel=1e-9)


def test_limite_elastique_vaut_fsd():
    a = Acier.b500b()
    eps_y = deformation_elastique(a)
    assert contrainte_acier(eps_y, a) == pytest.approx(fsd(a), rel=1e-9)


def test_symetrique_en_compression():
    a = Acier.b500b()
    eps = deformation_elastique(a) / 2.0
    assert contrainte_acier(-eps, a) == pytest.approx(-contrainte_acier(eps, a), rel=1e-9)


def test_ecrouissage_atteint_k_fois_fsd_a_epsilon_ud():
    a = Acier.b500b()
    sigma = contrainte_acier(a.epsilon_ud, a)
    assert sigma == pytest.approx(a.k_durcissement * fsd(a), rel=1e-9)


def test_ecrouissage_est_borne_au_dela_de_epsilon_ud():
    a = Acier.b500b()
    assert contrainte_acier(2.0 * a.epsilon_ud, a) == pytest.approx(a.k_durcissement * fsd(a), rel=1e-9)


def test_ecrouissage_point_intermediaire_est_lineaire():
    a = Acier.b500b()
    eps_y = deformation_elastique(a)
    eps = (eps_y + a.epsilon_ud) / 2.0
    pente = (a.k_durcissement * fsd(a) - fsd(a)) / (a.epsilon_ud - eps_y)
    attendu = fsd(a) + pente * (eps - eps_y)
    assert contrainte_acier(eps, a) == pytest.approx(attendu, rel=1e-9)


def test_contrainte_utilise_fsk_hors_calcul_elu():
    a = Acier.b500b()
    eps_yk = a.fsk / a.Es
    assert contrainte_acier(eps_yk, a, calcul=False) == pytest.approx(a.fsk, rel=1e-9)
