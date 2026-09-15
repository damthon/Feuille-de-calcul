import pytest

from mur_contre_terre.donnees.materiaux import Acier, Beton, Materiaux
from mur_contre_terre.section_ba.flexion_composee import (
    SectionRectangulaire,
    armature_minimale,
    armature_necessaire,
    equilibre,
)


def _materiaux() -> Materiaux:
    return Materiaux(
        beton=Beton.depuis_classe("C30/37"), acier=Acier.b500b(), enrobage_terre=0.05, enrobage_interieur=0.04
    )


def _section() -> SectionRectangulaire:
    return SectionRectangulaire(epaisseur=0.30, enrobage_terre=0.05, enrobage_interieur=0.04)


def test_section_epaisseur_non_positive_leve_une_erreur():
    with pytest.raises(ValueError):
        SectionRectangulaire(epaisseur=0.0, enrobage_terre=0.05, enrobage_interieur=0.04)


def test_section_enrobage_hors_domaine_leve_une_erreur():
    with pytest.raises(ValueError):
        SectionRectangulaire(epaisseur=0.30, enrobage_terre=0.35, enrobage_interieur=0.04)


def test_section_somme_enrobages_superieure_a_epaisseur_leve_une_erreur():
    with pytest.raises(ValueError):
        SectionRectangulaire(epaisseur=0.10, enrobage_terre=0.06, enrobage_interieur=0.06)


def test_section_positions_armature():
    s = _section()
    assert s.z_armature_terre == pytest.approx(0.05)
    assert s.z_armature_interieur == pytest.approx(0.26)


def test_armature_necessaire_face_invalide_leve_une_erreur():
    with pytest.raises(ValueError):
        armature_necessaire(0.0, 50e3, _section(), _materiaux(), face_tendue="autre")


@pytest.mark.parametrize("m_ed", [5e3, 20e3, 50e3, 100e3, 150e3])
def test_armature_necessaire_equilibre_exact_flexion_pure(m_ed):
    section, materiaux = _section(), _materiaux()
    r = armature_necessaire(n_ed=0.0, m_ed=m_ed, section=section, materiaux=materiaux, face_tendue="interieur")
    n, m = equilibre(r.profondeur_axe_neutre, r.armature_calculee, 0.0, section, materiaux, "interieur")
    assert n == pytest.approx(0.0, abs=1.0)
    assert m == pytest.approx(m_ed, abs=1.0)


def test_armature_necessaire_croit_avec_le_moment():
    section, materiaux = _section(), _materiaux()
    valeurs = [
        armature_necessaire(0.0, m_ed, section, materiaux, "interieur").armature_necessaire
        for m_ed in (20e3, 60e3, 100e3, 140e3)
    ]
    assert valeurs == sorted(valeurs)
    assert valeurs[-1] > valeurs[0]


def test_armature_necessaire_moment_faible_est_gouvernee_par_le_minimum():
    r = armature_necessaire(0.0, 5e3, _section(), _materiaux(), face_tendue="interieur")
    assert r.armature_calculee < r.armature_minimale
    assert r.armature_necessaire == pytest.approx(r.armature_minimale)


def test_armature_necessaire_face_terre_equilibre_exact():
    section, materiaux = _section(), _materiaux()
    # M_Ed < 0 tend la face terre, par convention (voir l'en-tête du module)
    r = armature_necessaire(0.0, -80e3, section, materiaux, face_tendue="terre")
    n, m = equilibre(r.profondeur_axe_neutre, r.armature_calculee, 0.0, section, materiaux, "terre")
    assert n == pytest.approx(0.0, abs=1.0)
    assert m == pytest.approx(-80e3, abs=1.0)


def test_armature_necessaire_compression_reduit_l_armature_requise():
    section, materiaux = _section(), _materiaux()
    sans_compression = armature_necessaire(0.0, 80e3, section, materiaux, "interieur").armature_calculee
    avec_compression = armature_necessaire(-200e3, 80e3, section, materiaux, "interieur").armature_calculee
    assert avec_compression < sans_compression


def test_armature_minimale_formule():
    section, materiaux = _section(), _materiaux()
    d = 0.25
    b = section.largeur
    fctm, fsk = materiaux.beton.fctm, materiaux.acier.fsk
    attendu = max(0.26 * fctm / fsk * b * d, 0.0013 * b * d)
    assert armature_minimale(section, materiaux, d) == pytest.approx(attendu)


def test_equilibre_armature_nulle_ne_retient_que_le_beton():
    section, materiaux = _section(), _materiaux()
    n, m = equilibre(0.02, 0.0, 0.0, section, materiaux, "interieur")
    n2, m2 = equilibre(0.02, 5e-4, 0.0, section, materiaux, "interieur")
    assert n2 > n  # armature tendue ajoute de la traction (N plus élevé)


def test_equilibre_x_non_positif_leve_une_erreur():
    with pytest.raises(ValueError):
        equilibre(0.0, 0.0, 0.0, _section(), _materiaux(), "interieur")


def test_equilibre_armature_negative_leve_une_erreur():
    with pytest.raises(ValueError):
        equilibre(0.02, -1e-4, 0.0, _section(), _materiaux(), "interieur")
