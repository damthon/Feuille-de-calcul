"""Géométrie du mur et de sa semelle avant.

Toutes les grandeurs sont en mètres. La paroi est modélisée en tranche de
1,00 m de longueur de mur, épaisseur interpolée linéairement entre le pied
(``z = 0``) et le couronnement (``z = hauteur``).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Geometrie:
    hauteur: float
    ep_base: float
    ep_couronnement: float
    debord_semelle: float
    ep_semelle: float

    def __post_init__(self) -> None:
        for nom in ("hauteur", "ep_base", "ep_couronnement", "debord_semelle", "ep_semelle"):
            valeur = getattr(self, nom)
            if valeur <= 0:
                raise ValueError(f"Geometrie.{nom} doit être strictement positif (reçu {valeur})")

    @property
    def largeur_semelle(self) -> float:
        """Largeur totale B de la semelle (épaisseur du mur à la base + débord).

        Sert au calcul de la rigidité en rotation kθ de l'encastrement
        élastique au pied (modèle de Winkler).
        """
        return self.ep_base + self.debord_semelle

    def epaisseur(self, z: float) -> float:
        """Épaisseur du mur à la cote ``z`` (0 au pied, ``hauteur`` en tête).

        Interpolation linéaire entre l'épaisseur à la base et celle au
        couronnement.
        """
        if not 0.0 <= z <= self.hauteur:
            raise ValueError(f"z={z} hors de la hauteur du mur [0, {self.hauteur}]")
        t = z / self.hauteur
        return self.ep_base + (self.ep_couronnement - self.ep_base) * t
