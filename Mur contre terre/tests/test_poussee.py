import math

import pytest

from mur_contre_terre.donnees.sol import Sol, TypePoussee
from mur_contre_terre.geotechnique.poussee import (
    coefficients_poussee,
    contrainte_verticale_effective,
    delta_actif_defaut,
    k0_jaky,
    kah_coulomb,
    pression_active_horizontale,
    pression_verticale,
    profil_poussee,
    E_AH_MIN,
)
from mur_contre_terre.unites import deg, kN_m3, MPa


def test_kah_coulomb_redonne_rankine_sans_frottement_ni_talus():
    phi = deg(30)
    attendu = (1 - math.sin(phi)) / (1 + math.sin(phi))
    assert kah_coulomb(phi, delta=0.0, beta=0.0) == pytest.approx(attendu, rel=1e-9)


def test_kah_coulomb_valeur_de_reference():
    # φ'=30°, δ=2φ'/3=20°, β=0, mur vertical — valeur de table classique ≈ 0.297
    kah = kah_coulomb(deg(30), delta=deg(20), beta=0.0)
    assert kah == pytest.approx(0.297, rel=2e-3)


def test_kah_coulomb_beta_superieur_a_phi_leve_une_erreur():
    with pytest.raises(ValueError):
        kah_coulomb(deg(20), delta=0.0, beta=deg(25))


def test_k0_jaky_terrain_horizontal():
    assert k0_jaky(deg(30)) == pytest.approx(0.5, rel=1e-9)


def test_k0_jaky_terrain_incline():
    # φ'=30°, β=10° — K0 = (1-sin30)(1+sin10)/cos10 ≈ 0.596
    assert k0_jaky(deg(30), deg(10)) == pytest.approx(0.596, rel=2e-3)


def test_k0_jaky_beta_superieur_a_phi_leve_une_erreur():
    with pytest.raises(ValueError):
        k0_jaky(deg(20), deg(25))


def test_delta_actif_defaut():
    phi = deg(30)
    assert delta_actif_defaut(phi, rugueux=True) == pytest.approx(2 * phi / 3)
    assert delta_actif_defaut(phi, rugueux=False) == 0.0


def test_coefficients_poussee_actif_utilise_delta_par_defaut():
    sol = Sol(gamma=kN_m3(18), phi=deg(30))  # delta non saisi, rugueux=True par défaut
    coeffs = coefficients_poussee(sol)
    assert coeffs.kah is not None
    assert coeffs.k0 is None
    assert coeffs.delta == pytest.approx(2 * deg(30) / 3)


def test_coefficients_poussee_au_repos():
    sol = Sol(gamma=kN_m3(18), phi=deg(30), type_poussee=TypePoussee.AU_REPOS)
    coeffs = coefficients_poussee(sol)
    assert coeffs.k0 is not None
    assert coeffs.kah is None


def test_contrainte_verticale_effective_sans_nappe():
    sol = Sol(gamma=kN_m3(18), phi=deg(30))
    assert contrainte_verticale_effective(sol, hauteur=3.0, profondeur=3.0) == pytest.approx(18e3 * 3.0)


def test_contrainte_verticale_effective_avec_nappe():
    sol = Sol(gamma=kN_m3(18), phi=deg(30), gamma_sat=kN_m3(20), niveau_nappe=2.0)
    # au-dessus de la nappe : gamma ; en dessous : gamma' = gamma_sat - gamma_eau
    gamma_prime = kN_m3(20) - 9.81e3
    attendu = 18e3 * 2.0 + gamma_prime * 1.0
    assert contrainte_verticale_effective(sol, hauteur=3.0, profondeur=3.0) == pytest.approx(attendu)


def test_contrainte_verticale_effective_avec_surcharge():
    sol = Sol(gamma=kN_m3(18), phi=deg(30))
    assert contrainte_verticale_effective(sol, hauteur=3.0, profondeur=1.0, g0=5e3) == pytest.approx(5e3 + 18e3)


def test_contrainte_verticale_effective_hors_domaine_leve_une_erreur():
    sol = Sol(gamma=kN_m3(18), phi=deg(30))
    with pytest.raises(ValueError):
        contrainte_verticale_effective(sol, hauteur=3.0, profondeur=3.5)


def test_pression_active_sans_cohesion():
    sol = Sol(gamma=kN_m3(18), phi=deg(30), delta=0.0)
    kah = kah_coulomb(deg(30), 0.0, 0.0)
    e_ah = pression_active_horizontale(sol, hauteur=3.0, profondeur=3.0)
    assert e_ah == pytest.approx(kah * 18e3 * 3.0)


def test_pression_active_avec_cohesion_plancher_pres_de_la_surface():
    sol = Sol(gamma=kN_m3(18), phi=deg(30), delta=0.0, c=MPa(0.02))  # 20 kPa de cohésion
    e_ah_surface = pression_active_horizontale(sol, hauteur=5.0, profondeur=0.0)
    assert e_ah_surface == pytest.approx(E_AH_MIN)


def test_pression_active_avec_cohesion_formule_en_profondeur():
    sol = Sol(gamma=kN_m3(18), phi=deg(30), delta=0.0, c=1.0)  # cohésion négligeable
    kah = kah_coulomb(deg(30), 0.0, 0.0)
    e_ah = pression_active_horizontale(sol, hauteur=5.0, profondeur=5.0)
    attendu = kah * 18e3 * 5.0 - 2.0 * 1.0 * math.sqrt(kah)
    assert e_ah == pytest.approx(attendu)
    assert e_ah > E_AH_MIN


def test_pression_verticale_actif_utilise_delta():
    e_av = pression_verticale(100.0, Sol(gamma=kN_m3(18), phi=deg(30), type_poussee=TypePoussee.ACTIF), delta=deg(20))
    assert e_av == pytest.approx(100.0 * math.tan(deg(20)))


def test_pression_verticale_au_repos_utilise_beta_pas_delta():
    sol = Sol(gamma=kN_m3(18), phi=deg(30), beta=deg(10), type_poussee=TypePoussee.AU_REPOS)
    e_av = pression_verticale(100.0, sol, delta=deg(20))  # delta ignoré au repos
    assert e_av == pytest.approx(100.0 * math.tan(deg(10)))


def test_pression_verticale_au_repos_terrain_horizontal_est_nulle():
    sol = Sol(gamma=kN_m3(18), phi=deg(30), type_poussee=TypePoussee.AU_REPOS)
    assert pression_verticale(100.0, sol, delta=deg(20)) == pytest.approx(0.0)


def test_profil_poussee_retourne_le_couple_horizontal_vertical():
    sol = Sol(gamma=kN_m3(18), phi=deg(30), delta=deg(20))
    e_ah, e_av = profil_poussee(sol, hauteur=3.0, profondeur=3.0)
    assert e_ah > 0
    assert e_av == pytest.approx(e_ah * math.tan(deg(20)))
