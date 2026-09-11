"""Matériaux — béton (SIA 262) et acier d'armature B500B.

Les propriétés mécaniques de base sont portées ici (Pa, sans dimension) ;
les lois contrainte-déformation avancées (parabole-rectangle, bilinéaire
écrouissable) sont implémentées au lot 5 dans ``section_ba``, à partir de
ces mêmes grandeurs.
"""

from __future__ import annotations

from dataclasses import dataclass

# fck, fctm, Ecm en MPa — SIA 262 tableau 4 (harmonisé avec EN 1992-1-1
# tableau 3.1). À recouper avec l'édition SIA au lot 5.
_CLASSES_BETON: dict[str, tuple[float, float, float]] = {
    "C20/25": (20.0, 2.2, 30000.0),
    "C25/30": (25.0, 2.6, 31000.0),
    "C30/37": (30.0, 2.9, 33000.0),
    "C35/45": (35.0, 3.2, 34000.0),
    "C40/50": (40.0, 3.5, 35000.0),
}


@dataclass(frozen=True)
class Beton:
    fck: float
    fctm: float
    Ecm: float
    epsilon_cu: float = 0.0035

    def __post_init__(self) -> None:
        for nom in ("fck", "fctm", "Ecm", "epsilon_cu"):
            valeur = getattr(self, nom)
            if valeur <= 0:
                raise ValueError(f"Beton.{nom} doit être strictement positif (reçu {valeur})")

    @classmethod
    def depuis_classe(cls, classe: str) -> "Beton":
        """Construit un béton à partir d'une classe SIA 262 (ex. ``"C30/37"``)."""
        try:
            fck, fctm, ecm = _CLASSES_BETON[classe]
        except KeyError:
            classes = ", ".join(sorted(_CLASSES_BETON))
            raise ValueError(f"Classe de béton inconnue : {classe!r} (disponibles : {classes})") from None
        from mur_contre_terre.unites import MPa

        return cls(fck=MPa(fck), fctm=MPa(fctm), Ecm=MPa(ecm))

    @staticmethod
    def classes_disponibles() -> tuple[str, ...]:
        return tuple(sorted(_CLASSES_BETON))


@dataclass(frozen=True)
class Acier:
    fsk: float = 500e6
    Es: float = 205e9
    epsilon_ud: float = 0.045

    def __post_init__(self) -> None:
        for nom in ("fsk", "Es", "epsilon_ud"):
            valeur = getattr(self, nom)
            if valeur <= 0:
                raise ValueError(f"Acier.{nom} doit être strictement positif (reçu {valeur})")

    @classmethod
    def b500b(cls) -> "Acier":
        return cls()


@dataclass(frozen=True)
class Materiaux:
    beton: Beton
    acier: Acier
    enrobage_terre: float
    enrobage_interieur: float

    def __post_init__(self) -> None:
        for nom in ("enrobage_terre", "enrobage_interieur"):
            valeur = getattr(self, nom)
            if valeur <= 0:
                raise ValueError(f"Materiaux.{nom} doit être strictement positif (reçu {valeur})")
